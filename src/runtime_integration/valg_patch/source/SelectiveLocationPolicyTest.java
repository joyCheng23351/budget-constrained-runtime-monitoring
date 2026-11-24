package com.runtimeverification.rvmonitor.java.rt.table.selection;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileWriter;

import org.junit.Test;

public class SelectiveLocationPolicyTest {
    @Test
    public void matchesNormalizedHistoricalLocations() throws Exception {
        File policy = File.createTempFile("valg-selection", ".tsv");
        File summary = File.createTempFile("valg-selection-summary", ".tsv");
        FileWriter writer = new FileWriter(policy);
        writer.write("specification\tlocation\n");
        writer.write("Appendable_ThreadSafeMonitor\t"
                + "p.C.m(C.java:12)41\n");
        writer.close();

        System.setProperty("valg.selection.file", policy.getAbsolutePath());
        System.setProperty("valg.selection.log", summary.getAbsolutePath());

        assertTrue(SelectiveLocationPolicy.isActive());
        assertTrue(SelectiveLocationPolicy.shouldCreate(
                "Appendable_ThreadSafe", "p.C(C.java:12)"));
        assertTrue(SelectiveLocationPolicy.shouldCreate(
                "Appendable_ThreadSafe", "p.C.append(C.java:12)"));
        assertFalse(SelectiveLocationPolicy.shouldCreate(
                "Appendable_ThreadSafe", "p.C.other(C.java:13)"));
        assertFalse(SelectiveLocationPolicy.shouldCreate(
                "StringBuilder_ThreadSafe", "p.C.m(C.java:12)"));
        SelectiveLocationPolicy.flushSummary();
        assertTrue(summary.length() > 0);
    }
}
