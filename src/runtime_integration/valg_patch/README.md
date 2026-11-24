# Valg instrumentation patch

`selective-location-policy.patch` is the actual source-level instrumentation
used for the runtime pilot. It applies to the official Valg repository and:

1. adds `SelectiveLocationPolicy.java` to `rv-monitor-rt`;
2. adds a Java unit test for policy normalization and decisions;
3. imports the policy runtime into generated JavaMOP aspects;
4. inserts the allowlist decision at the real parametric monitor-creation path;
5. disables the original RL decision only while an explicit allowlist is
   active; and
6. writes per-key create/skip counts to `VALG_SELECTION_LOG` at JVM shutdown.

Apply it with:

```bash
bash src/runtime_integration/apply_valg_patch.sh /absolute/path/to/Valg
```

The patch is intentionally stored instead of a forked copy of the entire Valg
repository so that every modified upstream line is reviewable. An absent
`VALG_SELECTION_FILE` preserves ordinary Valg behavior. An existing empty
policy rejects every candidate, which supports full/none/selected sanity
checks without rebuilding the agent.

For direct inspection, `source/SelectiveLocationPolicy.java` and
`source/SelectiveLocationPolicyTest.java` are snapshots of the two Java files
added to Valg by the patch. The patch remains the authoritative integration
artifact because it also contains the required edits to Valg's imports and
generated monitor-creation code.
