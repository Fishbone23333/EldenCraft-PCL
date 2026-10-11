package dev.eldencraft.bridge.client.mixin;

import dev.eldencraft.bridge.client.WorldProjectiles;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(BowItem.class)
abstract class WorldBowReleaseMixin {
  @Redirect(
      method = "releaseUsing",
      at = @At(value = "INVOKE", target = "Lnet/minecraft/world/item/BowItem;getPowerForTime(I)F"))
  private float eldencraft$quickShot(
      int ticks, ItemStack item, Level level, LivingEntity entity, int remaining) {
    float vanilla = BowItem.getPowerForTime(ticks);
    return WorldProjectiles.inSharedWorld(entity)
        ? dev.eldencraft.bridge.CampaignBowCharge.power(ticks, vanilla)
        : vanilla;
  }

  @Inject(method = "releaseUsing", at = @At("HEAD"), cancellable = true)
  private void eldencraft$cancelLostRelease(
      ItemStack item,
      Level level,
      LivingEntity player,
      int remaining,
      CallbackInfoReturnable<Boolean> cir) {
    if (!WorldProjectiles.permitItem(player)) cir.setReturnValue(false);
  }
}
