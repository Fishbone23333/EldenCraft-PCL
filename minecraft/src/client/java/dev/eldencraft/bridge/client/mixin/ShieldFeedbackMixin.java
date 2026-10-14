package dev.eldencraft.bridge.client.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import dev.eldencraft.bridge.client.ShieldFeedback;
import net.minecraft.client.renderer.FirstPersonHandsAndItemsRenderer;
import net.minecraft.world.entity.HumanoidArm;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(FirstPersonHandsAndItemsRenderer.class)
abstract class ShieldFeedbackMixin {
  @Inject(method = "applyItemArmTransform", at = @At("TAIL"))
  private void eldencraft$shieldImpact(PoseStack pose, HumanoidArm arm, float equip, CallbackInfo ci) {
    ShieldFeedback.transform(pose, arm);
  }
}
