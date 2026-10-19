# Partial reproduction of the Valg artifact

## Scope

The official Valg artifact was executed on four Java projects using no-RV,
ValgJ, JavaMOP, ValgT, and TraceMOP modes where the artifact completed.  These
runs validate the local Docker environment and provide preliminary baseline
measurements for later matched-cost experiments.  They do not reproduce the
paper's complete 64-project evaluation.

## Results

All four projects completed no-RV, ValgJ, and JavaMOP.  ValgJ was faster than
JavaMOP on xeger (32.3%), route53-infima (30.1%), and jlemmagen (63.7%), but
slower on javadbf (-57.4%).  The median ValgJ reduction relative to JavaMOP was
31.2%.  Each ValgJ/JavaMOP pair reported the same number of distinct violation
rows, although ValgJ reported fewer violation occurrences in every project.
This supports preservation of the observed violation signatures in these runs,
not a general violation-recall claim.

Only jlemmagen produced a complete ValgT/TraceMOP pair.  ValgT took 184.600 s
versus 349.056 s for TraceMOP, a 47.1% end-to-end reduction.  It retained 1,840
of 2,115 unique traces (87.0%) and reduced derived duplicate trace instances
from 1,258,457 to 79,812 (93.7%).

## Limitations

Each reported configuration was run once, so the data do not provide timing
uncertainty.  Three projects lack a complete trace-mode pair.  End-to-end time
includes the test workload and artifact setup; it is not the paper's
monitoring-only time.  These baseline measurements are also separate from the
offline location-selection experiment, whose budgets use event-check proxies.
