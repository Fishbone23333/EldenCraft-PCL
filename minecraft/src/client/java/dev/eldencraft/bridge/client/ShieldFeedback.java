package dev.eldencraft.bridge.client;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.HumanoidArm;

/** Confirmed native blocks animate the held shield, without a fake hurt event. */
public final class ShieldFeedback {
  private static Object player, level;
  private static long session, sequence, impact;

  private ShieldFeedback() {}

  public static void tick(Minecraft client) {
    var host = CampaignBridge.snapshot();
    if (host == null || client.player == null || !CampaignCombat.active(client.player)) {
      player = level = null;
      session = sequence = impact = 0;
      return;
    }
    if (player != client.player || level != client.level || session != host.session()) {
      player = client.player;
      level = client.level;
      session = host.session();
      sequence = host.damageEvents().stream().mapToLong(CampaignBridge.DamageEvent::seq).max().orElse(0);
      impact = 0;
      return;
    }
    for (var event : host.damageEvents()) {
      if (event.seq() <= sequence) continue;
      sequence = event.seq();
      if (event.blocked()) impact = System.nanoTime();
    }
  }

  public static void transform(PoseStack pose, HumanoidArm arm) {
    var owner = Minecraft.getInstance().player;
    if (owner == null || owner != player || !owner.isUsingItem()
        || !owner.getUseItem().has(DataComponents.BLOCKS_ATTACKS)) return;
    var usedArm = owner.getUsedItemHand() == InteractionHand.MAIN_HAND
        ? owner.getMainArm() : owner.getMainArm().getOpposite();
    long elapsed = System.nanoTime() - impact;
    if (arm != usedArm || impact == 0 || elapsed < 0 || elapsed >= 180_000_000L) return;
    float recoil = (float) Math.sin(Math.PI * elapsed / 180_000_000.0);
    pose.translate(0, -.025f * recoil, .12f * recoil);
    pose.mulPose(new org.joml.Matrix4f().rotationX((float) Math.toRadians(-8 * recoil)));
  }
}
