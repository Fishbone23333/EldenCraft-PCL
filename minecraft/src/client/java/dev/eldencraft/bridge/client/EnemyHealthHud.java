package dev.eldencraft.bridge.client;

import dev.eldencraft.bridge.*;
import java.util.*;
import net.fabricmc.fabric.api.client.rendering.v1.hud.*;
import net.minecraft.client.*;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.resources.Identifier;
import org.joml.Matrix4f;

/** Ordinary enemies and bosses share the native, LOS-verified head-gauge path. */
public final class EnemyHealthHud {
  private record Identity(long pid, long epoch, long map, long handle, long generation, float maxHp) {}
  private static final Map<Identity, HudDamageTrail> TRAILS = new HashMap<>();
  private static ProxyProtocol.Frame observed;
  private static long observedNanos;

  private EnemyHealthHud() {}

  public static void initialize() {
    HudElementRegistry.attachElementBefore(
        VanillaHudElements.BOSS_BAR,
        Identifier.fromNamespaceAndPath("eldencraft_bridge", "enemy_health"),
        EnemyHealthHud::extract);
  }

  /** Reuse the exact mailbox read already performed by picking; no additional IO per frame. */
  static void update(ProxyProtocol.Frame frame) {
    if (frame == null || !frame.ready()) {
      clear();
      return;
    }
    // A repeated target publication must not renew its display lifetime.
    if (observed == null || observed.pid() != frame.pid() || observed.epoch() != frame.epoch()
        || observed.map() != frame.map() || observed.frame() != frame.frame())
      observedNanos = System.nanoTime();
    observed = frame;
  }

  private static void extract(GuiGraphicsExtractor gui, DeltaTracker delta) {
    var client = Minecraft.getInstance();
    var settings = CampaignConfig.current().hud.enemyBar();
    var frame = observed;
    var pose = HostController.frame();
    var avatar = HostController.avatar();
    var control = HostController.combatSnapshot(client);
    long now = System.nanoTime();
    if (!settings.enabled() || !CampaignCombat.active(client.player)
        || client.gui.hud.isHidden() || client.gui.screen() != null
        || !SceneCapture.active() || pose == null || avatar == null || control == null
        || !EnemyHealthDisplay.sameContext(frame, control.publisherPid(), control.mapId(),
            now - observedNanos)) {
      TRAILS.clear();
      return;
    }
    // The ECTG boxes are relative to the host feet. Use this frame's actual F5 camera,
    // not the server's 20 Hz stand-in or the combat ray (which differs in front view).
    var camera = new ProxyProtocol.Vec(
        pose.x() - avatar.x(), pose.y() - avatar.y(), pose.z() - avatar.z());
    double yaw = Math.toRadians(pose.yaw()), pitch = Math.toRadians(pose.pitch());
    var forward = new ProxyProtocol.Vec(
        -Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
    var lens = client.gameRenderer.gameRenderState().levelRenderState.cameraRenderState.projectionMatrix;
    var viewProjection = new Matrix4f(lens).mul(ProxyView.rotation(forward));
    var colors = CampaignConfig.current().hud.bossBar();
    var retained = new HashSet<Identity>();
    for (var target : frame.targets()) {
      if (!EnemyHealthDisplay.visible(target, settings.maxDistance())) continue;
      var position = EnemyHealthDisplay.project(
          EnemyHealthDisplay.head(target, settings.headOffset()), camera, viewProjection,
          gui.guiWidth(), gui.guiHeight(), settings.width(), settings.height(), settings.showNumbers());
      if (position == null) continue;
      var id = new Identity(frame.pid(), frame.epoch(), frame.map(), target.handle(),
          target.generation(), target.maxHp());
      retained.add(id);
      double fraction = (double) target.hp() / target.maxHp();
      double trail = TRAILS.computeIfAbsent(id, ignored -> new HudDamageTrail()).update(
          id.toString(), fraction, now, colors.damageHoldSeconds(), colors.damageTrailPerSecond());
      int x = position.x(), y = position.y(), width = settings.width(), height = settings.height();
      CampaignHud.frame(gui, x, y, width, height, colors.border(), colors.background());
      int inner = width - 4;
      int delayed = (int) Math.round(inner * trail), filled = (int) Math.round(inner * fraction);
      if (delayed > 0) gui.fill(x + 2, y + 2, x + 2 + delayed, y + height - 2, colors.trailTint());
      if (filled > 0) gui.fill(x + 2, y + 2, x + 2 + filled, y + height - 2, colors.fillTint());
      if (settings.showNumbers()) {
        String text = Math.round(target.hp()) + " / " + Math.round(target.maxHp());
        float scale = Math.min(.65f, (width - 4f) / Math.max(1, client.font.width(text)));
        gui.pose().pushMatrix();
        gui.pose().scale(scale, scale);
        gui.text(client.font, text,
            (int) ((x + (width - client.font.width(text) * scale) / 2) / scale),
            (int) ((y - 8) / scale), colors.text(), true);
        gui.pose().popMatrix();
      }
    }
    TRAILS.keySet().retainAll(retained);
  }

  static void clear() {
    observed = null;
    observedNanos = 0;
    TRAILS.clear();
  }
}
