package com.runtimeverification.rvmonitor.java.rt.table.selection;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.reflect.SourceLocation;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Optional deterministic monitor-creation allowlist for Valg.
 *
 * <p>The policy is disabled when neither {@code -Dvalg.selection.file} nor
 * {@code VALG_SELECTION_FILE} is set. When enabled, the file must be a TSV with
 * two columns: specification and stable source location. The specification may
 * include or omit the trailing {@code Monitor}. Locations are canonicalized to
 * the enclosing type plus file and line, for example {@code p.C(C.java:12)}.
 * This avoids a mismatch between historical first-event method names and the
 * runtime API-event join point method name.</p>
 */
public final class SelectiveLocationPolicy {
    private static final String FILE_PROPERTY = "valg.selection.file";
    private static final String LOG_PROPERTY = "valg.selection.log";
    private static final String FILE_ENV = "VALG_SELECTION_FILE";
    private static final String LOG_ENV = "VALG_SELECTION_LOG";

    private static final Set<String> ALLOWED;
    private static final boolean ACTIVE;
    private static final String SUMMARY_PATH;
    private static final ConcurrentHashMap<String, DecisionCounter> COUNTERS =
            new ConcurrentHashMap<String, DecisionCounter>();
    private static final AtomicLong TOTAL_ATTEMPTS = new AtomicLong();
    private static final AtomicLong TOTAL_CREATED = new AtomicLong();
    private static final AtomicLong TOTAL_SKIPPED = new AtomicLong();

    static {
        String policyPath = firstNonEmpty(System.getProperty(FILE_PROPERTY),
                System.getenv(FILE_ENV));
        SUMMARY_PATH = firstNonEmpty(System.getProperty(LOG_PROPERTY),
                System.getenv(LOG_ENV));
        if (policyPath == null) {
            ACTIVE = false;
            ALLOWED = Collections.emptySet();
        } else {
            ACTIVE = true;
            ALLOWED = Collections.unmodifiableSet(loadPolicy(policyPath));
            Runtime.getRuntime().addShutdownHook(new Thread(new Runnable() {
                @Override
                public void run() {
                    flushSummary();
                }
            }, "valg-selection-summary"));
        }
    }

    private SelectiveLocationPolicy() {
    }

    public static boolean isActive() {
        return ACTIVE;
    }

    public static boolean shouldCreate(String specification,
            JoinPoint.StaticPart joinpoint) {
        return shouldCreate(specification, stableLocation(joinpoint));
    }

    /** Visible as an overload so policy matching can be tested without weaving. */
    public static boolean shouldCreate(String specification, String location) {
        if (!ACTIVE) {
            return true;
        }
        String key = key(specification, location);
        boolean create = ALLOWED.contains(key);
        TOTAL_ATTEMPTS.incrementAndGet();
        if (create) {
            TOTAL_CREATED.incrementAndGet();
        } else {
            TOTAL_SKIPPED.incrementAndGet();
        }
        DecisionCounter counter = COUNTERS.get(key);
        if (counter == null) {
            DecisionCounter fresh = new DecisionCounter();
            DecisionCounter previous = COUNTERS.putIfAbsent(key, fresh);
            counter = previous == null ? fresh : previous;
        }
        if (create) {
            counter.created.incrementAndGet();
        } else {
            counter.skipped.incrementAndGet();
        }
        return create;
    }

    public static String stableLocation(JoinPoint.StaticPart joinpoint) {
        if (joinpoint == null) {
            return "<unknown>";
        }
        SourceLocation source = joinpoint.getSourceLocation();
        String owner = source != null && source.getWithinType() != null
                ? source.getWithinType().getName() : "<unknown>";
        String fileLine = source == null ? "<unknown>" : source.toString();
        return owner + "(" + fileLine + ")";
    }

    public static String normalizeSpecification(String specification) {
        String value = specification == null ? "" : specification.trim();
        if (value.endsWith("Monitor")) {
            value = value.substring(0, value.length() - "Monitor".length());
        }
        return value;
    }

    public static String normalizeLocation(String location) {
        String value = location == null ? "" : location.trim();
        // Historical TraceMOP exports append a numeric location ID after ')'.
        value = value.replaceFirst("\\)\\d+$", ")");
        int open = value.lastIndexOf('(');
        int close = value.lastIndexOf(')');
        if (open <= 0 || close <= open) {
            return value;
        }
        String ownerOrMethod = value.substring(0, open);
        String fileLine = value.substring(open + 1, close);
        int colon = fileLine.lastIndexOf(':');
        String file = colon < 0 ? fileLine : fileLine.substring(0, colon);
        String fileBase = file.endsWith(".java")
                ? file.substring(0, file.length() - 5) : file;
        int lastDot = ownerOrMethod.lastIndexOf('.');
        String lastSegment = lastDot < 0 ? ownerOrMethod
                : ownerOrMethod.substring(lastDot + 1);
        // An already canonical value ends in the class name. A historical
        // value ends in the first-event method name, so remove that segment.
        if (lastDot > 0 && !lastSegment.equals(fileBase)) {
            ownerOrMethod = ownerOrMethod.substring(0, lastDot);
        }
        return ownerOrMethod + "(" + fileLine + ")";
    }

    public static String key(String specification, String location) {
        return normalizeSpecification(specification) + "\t"
                + normalizeLocation(location);
    }

    public static synchronized void flushSummary() {
        if (!ACTIVE || SUMMARY_PATH == null) {
            return;
        }
        File output = new File(SUMMARY_PATH);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        List<String> keys = new ArrayList<String>(COUNTERS.keySet());
        Collections.sort(keys, new Comparator<String>() {
            @Override
            public int compare(String left, String right) {
                return left.compareTo(right);
            }
        });
        try {
            BufferedWriter writer = new BufferedWriter(new FileWriter(output));
            writer.write("specification\tlocation\tcreated\tskipped\n");
            for (String key : keys) {
                DecisionCounter counter = COUNTERS.get(key);
                String[] parts = key.split("\\t", 2);
                writer.write(parts[0]);
                writer.write('\t');
                writer.write(parts.length > 1 ? parts[1] : "");
                writer.write('\t');
                writer.write(Long.toString(counter.created.get()));
                writer.write('\t');
                writer.write(Long.toString(counter.skipped.get()));
                writer.write('\n');
            }
            writer.write("__TOTAL__\t\t");
            writer.write(Long.toString(TOTAL_CREATED.get()));
            writer.write('\t');
            writer.write(Long.toString(TOTAL_SKIPPED.get()));
            writer.write('\n');
            writer.close();
        } catch (IOException error) {
            System.err.println("[Valg selection] unable to write summary: "
                    + error.getMessage());
        }
    }

    private static Set<String> loadPolicy(String path) {
        Set<String> allowed = new HashSet<String>();
        try {
            BufferedReader reader = new BufferedReader(new FileReader(path));
            String line;
            while ((line = reader.readLine()) != null) {
                String value = line.trim();
                if (value.length() == 0 || value.startsWith("#")
                        || value.startsWith("specification\t")) {
                    continue;
                }
                String[] parts = value.split("\\t", 2);
                if (parts.length != 2) {
                    reader.close();
                    throw new IllegalArgumentException(
                            "Invalid policy row (expected two TSV columns): " + line);
                }
                allowed.add(key(parts[0], parts[1]));
            }
            reader.close();
        } catch (IOException error) {
            throw new IllegalStateException("Unable to load Valg selection policy "
                    + path, error);
        }
        System.err.println("[Valg selection] loaded " + allowed.size()
                + " location/specification pairs from " + path);
        return allowed;
    }

    private static String firstNonEmpty(String first, String second) {
        if (first != null && first.trim().length() > 0) {
            return first.trim();
        }
        if (second != null && second.trim().length() > 0) {
            return second.trim();
        }
        return null;
    }

    private static final class DecisionCounter {
        private final AtomicLong created = new AtomicLong();
        private final AtomicLong skipped = new AtomicLong();
    }
}
