//! Enter confirmed guest hits into ER's own floating-gauge registry.
//! The calculated-HP sink bypasses the native attack dispatcher, so registration
//! must not depend on having an ER lock-on target. Native FE owns rendering,
//! projection, occlusion, damage numbers, eight slots and display expiration.
use eldenring::cs::{CSCam, CSCamera, CSFeManImp, FieldInsHandle, PlayerIns};
use ilhook::x64::{HookFlags, Registers, hook_closure_retn};
use fromsoftware_shared::{FromStatic, program::Program};
use pelite::pe64::PeObject;
use std::sync::{Mutex, OnceLock, atomic::{AtomicBool, Ordering}};

// Native normal-enemy projection takes a CSPersCam in R8 (near plane at
// +0x58, CSCam::view/projection at 0x681550). Its original caller uses the menu
// camera. Select the camera actually controlled by our first-person driver.
// Do not call the update twice: it also advances the native 1.5s expiry clock.
const PROJECT: usize = 0x7778b0;
const PROJECT_PREFIX: &[u8] = &[0x48, 0x8b, 0xc4, 0x55, 0x41, 0x54, 0x41, 0x55,
    0x41, 0x56, 0x41, 0x57, 0x48, 0x8d, 0xa8, 0x28, 0xfe, 0xff, 0xff];
#[derive(Clone, Copy)]
struct View {
    player: usize,
    issued: u64,
    matrix: [[f32; 4]; 4],
    fov: f32,
    near: f32,
}
impl View {
    fn fresh(self, player: usize, now: u64) -> bool {
        self.player != 0 && self.player == player && now >= self.issued && now - self.issued < 100
            && self.matrix.iter().flatten().all(|v| v.is_finite())
            && self.fov.is_finite() && (0.05..3.13).contains(&self.fov)
            && self.near.is_finite() && (0.0..1.0).contains(&self.near)
    }
}
static VIEW: Mutex<Option<View>> = Mutex::new(None);
static FAULTED: AtomicBool = AtomicBool::new(false);

pub unsafe fn authorize_view(active: bool) {
    let permit = if active { (|| {
        let player = unsafe { PlayerIns::local_player() }.ok()? as *const _ as usize;
        let cameras = unsafe { CSCamera::instance() }.ok()?;
        let camera = cameras.pers_cam_1.as_ref();
        let vector = |v: fromsoftware_shared::F32Vector4| [v.0, v.1, v.2, v.3];
        Some(View { player, issued: crate::world_transport::now(),
            matrix: [vector(camera.matrix.0), vector(camera.matrix.1), vector(camera.matrix.2), vector(camera.matrix.3)],
            fov: camera.fov, near: camera.near_plane })
    })() } else { None };
    if let Ok(mut view) = VIEW.lock() { *view = permit; }
}

/// Called once after executable verification; hosting owns hook restoration.
pub unsafe fn install() -> Result<(), String> {
    let image = Program::current().image();
    if image.get(PROJECT..PROJECT + PROJECT_PREFIX.len()) != Some(PROJECT_PREFIX)
        || image.get(0xb02070..0xb02075) != Some(&[0xe8, 0x3b, 0x58, 0xc7, 0xff]) {
        return Err("native enemy projection fingerprints do not match".into());
    }
    let address = image.as_ptr() as usize + PROJECT;
    let callback = |registers: *mut Registers, original: usize| -> usize {
        // Keep the copied camera alive for the complete original call. CameraStep
        // can overwrite pers_cam_1 before the next menu update; reading its live
        // pointer here would silently project with the third-person camera again.
        let replacement = std::panic::catch_unwind(|| unsafe {
            if FAULTED.load(Ordering::Acquire) || crate::hosting::shutting_down()
                || crate::engine::eldencraft_passthrough_active() == 0 { return None; }
            let view = VIEW.try_lock().ok().and_then(|v| *v)?;
            let now = crate::world_transport::now();
            let player = PlayerIns::local_player().ok()? as *const _ as usize;
            if !view.fresh(player, now) || (*registers).r8 == 0 { return None; }
            // CSCam contains scalar fields only and has no owning/drop fields.
            let mut camera = std::ptr::read((*registers).r8 as *const CSCam);
            let vector = |v: [f32; 4]| fromsoftware_shared::F32Vector4(v[0], v[1], v[2], v[3]);
            camera.matrix.0 = vector(view.matrix[0]);
            camera.matrix.1 = vector(view.matrix[1]);
            camera.matrix.2 = vector(view.matrix[2]);
            camera.matrix.3 = vector(view.matrix[3]);
            camera.fov = view.fov;
            camera.near_plane = view.near;
            Some(camera)
        });
        let camera = match replacement {
            Ok(camera) => camera,
            Err(_) => { FAULTED.store(true, Ordering::Release); None }
        };
        type Project = unsafe extern "system" fn(usize, f32, *const CSCam) -> usize;
        let project: Project = unsafe { std::mem::transmute(original) };
        let regs = unsafe { &*registers };
        unsafe { project(regs.rcx as usize, f32::from_bits(regs.xmm1 as u32),
            camera.as_ref().map_or(regs.r8 as *const CSCam, |c| c as *const CSCam)) }
    };
    let hook = unsafe { crate::hosting::hook(address, |option|
        hook_closure_retn(address, callback, option, HookFlags::empty())) }
        .map_err(|e| format!("native enemy camera hook: {e:?}"))?;
    std::mem::forget(hook);
    Ok(())
}

const REGISTER: usize = 0x76f530;
const PREFIX: &[u8] = &[
    0x48, 0x83, 0xec, 0x38, 0x0f, 0xb6, 0x44, 0x24, 0x60,
    0x48, 0x81, 0xc1, 0xf0, 0x59, 0, 0, 0x88, 0x44, 0x24, 0x20,
    0xe8, 0xe7, 0xa4, 0, 0, 0xb0, 1, 0x48, 0x83, 0xc4, 0x38, 0xc3,
];

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct EntryState(i32, u32, u32, u32);

/// Copy observations only; no frontend references span native feedback calls.
pub unsafe fn entry_state(target: FieldInsHandle) -> Option<EntryState> {
    let frontend = unsafe { CSFeManImp::instance() }.ok()?;
    let tag = frontend.enemy_chr_tag_displays.iter().find(|tag| tag.field_ins_handle == target)?;
    Some(EntryState(tag.damage_taken, tag.pre_damage_hp,
        tag.last_update_time_delta.to_bits(), tag.last_damage_time_delta.to_bits()))
}

/// Game task only, following successful damage and fresh instance readback.
/// Uses the same five-argument wrapper as the game's 0x449b43 notification.
pub unsafe fn damaged(target: FieldInsHandle, damage: i32, previous_hp: i32, boss: bool, before: Option<EntryState>) {
    if boss || target.is_empty() || damage <= 0 || previous_hp <= 0 {
        return;
    }
    static VERIFIED: OnceLock<bool> = OnceLock::new();
    let image = Program::current().image();
    if !*VERIFIED.get_or_init(|| image.get(REGISTER..REGISTER + PREFIX.len()) == Some(PREFIX)) {
        return;
    }
    // Native notify may have registered this hit. Compare copied state, since
    // rapid hits retain the first pre-damage HP while accumulating numbers.
    let after = unsafe { entry_state(target) };
    if after.is_some() && after != before {
        return;
    }
    let Ok(frontend) = (unsafe { CSFeManImp::instance_mut() }) else { return; };
    type Register = unsafe extern "system" fn(*mut CSFeManImp, FieldInsHandle, i32, i32, u8) -> u8;
    let register: Register = unsafe { std::mem::transmute(image.as_ptr() as usize + REGISTER) };
    unsafe { register(frontend, target, damage, previous_hp, 0); }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn first_person_gauge_camera_expires_and_cannot_cross_players() {
        let view = View { player: 7, issued: 1000, matrix: [[0.; 4]; 4], fov: 1.2, near: 0.05 };
        assert!(view.fresh(7, 1099));
        assert!(!view.fresh(8, 1001));
        assert!(!view.fresh(7, 999));
        assert!(!view.fresh(7, 1100));
        assert!(!View { fov: f32::NAN, ..view }.fresh(7, 1001));
        assert!(!View { near: -1., ..view }.fresh(7, 1001));
        assert!(!std::mem::needs_drop::<CSCam>());
        assert_eq!(std::mem::offset_of!(CSCam, near_plane), 0x58);
    }
}
