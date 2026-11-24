#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) normalizePath(args[[1]]) else normalizePath(".")
out <- if (length(args) >= 2) args[[2]] else file.path(root, "results", "final_presentation", "figures")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

navy <- "#142C44"
teal <- "#2FB9AE"
coral <- "#FF8266"
gold <- "#E8B84A"
gray <- "#6F7D8C"
light <- "#E8EEF3"

open_png <- function(name, width = 1800, height = 920) {
  png(file.path(out, name), width = width, height = height, res = 180, bg = "white")
  par(family = "sans", fg = navy, col.axis = navy, col.lab = navy, col.main = navy)
}

metrics <- read.csv(file.path(root, "results", "runtime", "validation", "javadbf-b20-greedy-5runs-metrics.csv"), check.names = FALSE)
metrics$memory_mib <- metrics$peak_container_memory_kb / 1024

# Figure 1: repeated-run time and memory.
open_png("figure1_runtime_memory_repetitions.png")
par(mfrow = c(1, 2), mar = c(5, 5, 4.5, 1.5), oma = c(0, 0, 2, 0))
plot(metrics$repetition, metrics$elapsed_seconds, type = "o", pch = 19, lwd = 2.8,
     col = teal, ylim = c(0, max(metrics$elapsed_seconds) * 1.18),
     xlab = "Repetition", ylab = "Elapsed time (s)", xaxt = "n",
     main = "End-to-end runtime")
axis(1, at = metrics$repetition)
grid(nx = NA, ny = NULL, col = light, lty = 1)
abline(h = mean(metrics$elapsed_seconds), col = coral, lwd = 2.5, lty = 2)
text(metrics$repetition, metrics$elapsed_seconds, labels = sprintf("%.1f", metrics$elapsed_seconds),
     pos = 3, cex = 0.85, col = navy)
legend("topright", legend = sprintf("Mean %.2f s; SD %.2f s", mean(metrics$elapsed_seconds), sd(metrics$elapsed_seconds)),
       col = coral, lty = 2, lwd = 2.5, bty = "n", cex = 0.88)

plot(metrics$repetition, metrics$memory_mib, type = "o", pch = 19, lwd = 2.8,
     col = coral, ylim = c(min(metrics$memory_mib) - 30, max(metrics$memory_mib) + 30),
     xlab = "Repetition", ylab = "Peak container memory (MiB)", xaxt = "n",
     main = "Peak container memory")
axis(1, at = metrics$repetition)
grid(nx = NA, ny = NULL, col = light, lty = 1)
abline(h = mean(metrics$memory_mib), col = teal, lwd = 2.5, lty = 2)
text(metrics$repetition, metrics$memory_mib, labels = sprintf("%.0f", metrics$memory_mib),
     pos = 3, cex = 0.85, col = navy)
legend("bottomright", legend = sprintf("Mean %.1f MiB; SD %.1f MiB", mean(metrics$memory_mib), sd(metrics$memory_mib)),
       col = teal, lty = 2, lwd = 2.5, bty = "n", cex = 0.88)
mtext("javadbf: 20% proxy-budget redundancy-aware greedy policy, five fresh JVM executions", outer = TRUE, cex = 1.15, font = 2, col = navy)
dev.off()

# Load decision totals from all five repeat logs.
decision_files <- list.files(file.path(root, "results", "runtime", "validation"),
                             pattern = "javadbf-b20-greedy-5runs-r[1-5]\\.selection-decisions\\.tsv$",
                             full.names = TRUE)
created <- skipped <- numeric(length(decision_files))
for (i in seq_along(decision_files)) {
  d <- read.delim(decision_files[[i]], check.names = FALSE)
  d <- d[d$specification != "__TOTAL__", ]
  created[[i]] <- sum(d$created)
  skipped[[i]] <- sum(d$skipped)
}

# Figure 2: monitor decision reproducibility and proportions.
open_png("figure2_monitor_creation_decisions.png")
par(mfrow = c(1, 2), mar = c(5, 5, 4.5, 1.5), oma = c(0, 0, 2, 0))
decision_mat <- rbind(created, skipped)
bp <- barplot(decision_mat, beside = TRUE, log = "y", col = c(coral, teal), border = NA,
              names.arg = seq_along(created), xlab = "Repetition", ylab = "Decision count (log scale)",
              main = "Identical decisions across runs", ylim = c(1000, 500000))
grid(nx = NA, ny = NULL, col = light, lty = 1)
legend(2.0, 450000, legend = c("Created", "Skipped"), fill = c(coral, teal),
       border = NA, bty = "n", horiz = TRUE)
text(bp[1, ], created, labels = format(created, big.mark = ","), pos = 3, cex = 0.78, col = navy)
text(bp[2, ], skipped, labels = format(skipped, big.mark = ","), pos = 3, cex = 0.78, col = navy)

total_created <- created[[1]]
total_skipped <- skipped[[1]]
proportions <- 100 * c(total_created, total_skipped) / (total_created + total_skipped)
barplot(matrix(proportions, ncol = 1), horiz = TRUE, col = c(coral, teal), border = NA,
        xlim = c(0, 100), axes = FALSE, main = "Share of creation attempts")
axis(1, at = seq(0, 100, 20), labels = paste0(seq(0, 100, 20), "%"))
arrows(18, 1.05, proportions[[1]] / 2, 0.82, length = 0.08, col = coral, lwd = 2)
text(18, 1.10, sprintf("Created %.2f%%", proportions[[1]]), col = coral, font = 2, cex = 0.95)
text(proportions[[1]] + proportions[[2]] / 2, 0.7, sprintf("Skipped %.2f%%", proportions[[2]]), col = "white", font = 2, cex = 1.05)
text(50, 0.30, sprintf("Created %s     Skipped %s",
                       format(total_created, big.mark = ","), format(total_skipped, big.mark = ",")),
     col = navy, cex = 0.9)
mtext("The policy reached the real monitor-creation path and produced deterministic decisions", outer = TRUE, cex = 1.15, font = 2, col = navy)
dev.off()

# Figure 3: baseline artifact comparison.
baseline <- read.csv(file.path(root, "results", "valg_baselines", "summary", "runtime_comparison.csv"), check.names = FALSE)
open_png("figure3_valgj_javamop_runtime_comparison.png")
par(mar = c(6, 5, 4.5, 2))
runtime_mat <- rbind(baseline$no_rv_seconds, baseline$valgj_seconds, baseline$javamop_seconds)
bp <- barplot(runtime_mat, beside = TRUE, col = c(gray, teal, coral), border = NA,
              names.arg = baseline$project, las = 1, ylab = "End-to-end time (s)",
              main = "Valg artifact reproduction: Java-mode runtime", ylim = c(0, max(runtime_mat) * 1.18))
grid(nx = NA, ny = NULL, col = light, lty = 1)
legend("topleft", legend = c("No RV", "ValgJ", "JavaMOP"), fill = c(gray, teal, coral), border = NA, bty = "n", horiz = TRUE)
text(bp, runtime_mat, labels = sprintf("%.1f", runtime_mat), pos = 3, cex = 0.72, col = navy)
mtext("Single-run artifact reproduction; values are recorded end-to-end seconds", side = 1, line = 4.5, cex = 0.9, col = gray)
dev.off()

# Figure 4: offline trace recall at 20% proxy budget.
offline <- read.csv(file.path(root, "results", "offline", "metrics_summary.csv"), check.names = FALSE)
offline <- offline[offline$budget_pct == 20, ]
algorithm_order <- c("random", "frequency", "utility_cost", "redundancy_greedy", "knapsack_additive")
labels <- c("Random", "Frequency", "Utility /\ncost", "Redundancy\ngreedy", "Additive\nknapsack")
vals <- sapply(c("javadbf", "jlemmagen"), function(project) {
  x <- offline[offline$project == project, ]
  100 * x$mean_trace_recall[match(algorithm_order, x$algorithm)]
})
open_png("figure4_offline_trace_recall_20pct.png")
par(mar = c(7, 5, 4.5, 2))
bp <- barplot(t(vals), beside = TRUE, col = c(teal, coral), border = NA,
              names.arg = labels, las = 1, ylab = "Historical unique-trace recall (%)",
              main = "Offline selection at 20% event-check proxy budget", ylim = c(0, 120))
grid(nx = NA, ny = NULL, col = light, lty = 1)
legend("top", legend = c("javadbf", "jlemmagen"), fill = c(teal, coral), border = NA, bty = "n", horiz = TRUE)
text(bp, t(vals), labels = sprintf("%.1f%%", t(vals)), pos = 3, cex = 0.75, col = navy)
mtext("Historical replay only; proxy budget is not measured runtime", side = 1, line = 5.2, cex = 0.9, col = gold, font = 2)
dev.off()

cat("Figures written to", normalizePath(out), "\n")
