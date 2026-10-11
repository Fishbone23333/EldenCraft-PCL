package dev.eldencraft.bridge;

/** Campaign quick shots keep vanilla's charge curve, with a minimum launch speed for a tap. */
public final class CampaignBowCharge {
  private CampaignBowCharge() {}

  public static float power(int ticks, float vanilla) {
    return ticks > 0 ? Math.max(.1f, vanilla) : vanilla;
  }
}
