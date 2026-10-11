package dev.eldencraft.bridge;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.LinkedHashMap;

/** Bounded, replaceable live-state mailboxes. Disk stalls never run on a game thread. */
public final class LatestStatePublisher implements AutoCloseable {
  @FunctionalInterface
  public interface Writer {
    void write(Path target, String payload) throws IOException;
  }

  private record State(String payload, long deadline) {}

  private final LinkedHashMap<Path, State> pending = new LinkedHashMap<>();
  private final Writer writer;
  private final Thread worker;
  private boolean closed;
  private long lastWarning;

  public LatestStatePublisher(String name) {
    this(name, LatestStatePublisher::writeAtomic);
  }

  public LatestStatePublisher(String name, Writer writer) {
    this.writer = writer;
    worker = new Thread(this::run, name);
    worker.setDaemon(true);
    worker.start();
  }

  /** Only the newest snapshot per channel survives congestion; old leases are never renewed. */
  public synchronized void offer(Path target, String payload, long lifetimeMillis) {
    if (closed) return;
    if (lifetimeMillis <= 0 || lifetimeMillis > 1500)
      throw new IllegalArgumentException("state lifetime");
    if (!pending.containsKey(target) && pending.size() >= 8)
      throw new IllegalStateException("too many live-state channels");
    pending.put(target, new State(payload, System.nanoTime() + lifetimeMillis * 1_000_000L));
    notifyAll();
  }

  private void run() {
    try {
      while (true) {
        Path path;
        State state;
        synchronized (this) {
          while (pending.isEmpty() && !closed) wait();
          if (closed) return;
          var entry = pending.entrySet().iterator().next();
          path = entry.getKey();
          state = entry.getValue();
          pending.remove(path);
        }
        if (System.nanoTime() > state.deadline()) continue;
        try {
          writer.write(path, state.payload());
        } catch (IOException error) {
          long now = System.nanoTime();
          if (now - lastWarning >= 5_000_000_000L) {
            lastWarning = now;
            org.slf4j.LoggerFactory.getLogger("eldencraft_state")
                .warn("Live-state publication delayed: {}: {}", path.getFileName(), error.toString());
          }
          // Windows readers/antivirus may briefly hold the destination. Retry on this
          // worker, yielding to newer snapshots and to the other mailbox channels.
          Thread.sleep(5);
          synchronized (this) {
            if (!closed && System.nanoTime() <= state.deadline()) pending.putIfAbsent(path, state);
          }
        }
      }
    } catch (InterruptedException shutdown) {
      Thread.currentThread().interrupt();
    }
  }

  public static void writeAtomic(Path target, String payload) throws IOException {
    Files.createDirectories(target.getParent());
    Path temporary = target.resolveSibling(target.getFileName() + ".pcl-state.tmp");
    Files.writeString(temporary, payload, StandardCharsets.UTF_8);
    // Live state expires in milliseconds. Atomic visibility is necessary; physical
    // fsync durability is not. Transactions and saved progression use their own path.
    Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
  }

  @Override
  public void close() {
    synchronized (this) {
      closed = true;
      pending.clear();
      notifyAll();
    }
    worker.interrupt();
    try {
      worker.join(1000);
    } catch (InterruptedException shutdown) {
      Thread.currentThread().interrupt();
    }
  }
}
