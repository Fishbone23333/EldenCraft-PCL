package dev.eldencraft.bridge;

/** Collect host wheel edges between Minecraft ticks, without replaying frame publications. */
public final class HostScrollInput {
  private long sequence = -1;
  private int pending;

  public void reset(long baseline) {
    sequence = baseline;
    pending = 0;
  }

  public void observe(long nextSequence, int wheel) {
    if (nextSequence == sequence) return;
    sequence = nextSequence;
    // Only the final hotbar slot matters; a fast scroll never builds a work backlog.
    pending = (pending + wheel) % 9;
  }

  public int take() {
    int value = pending;
    pending = 0;
    return value;
  }
}
