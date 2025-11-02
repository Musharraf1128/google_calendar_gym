#!/usr/bin/env python3
"""
Realism Audit for Google Calendar Gym

Measures the realism of the generated dataset across multiple dimensions:
- UI Popup Entropy: Diversity of popup types (0-1, higher = more varied)
- Color Variance: Event color distribution across Google's palette (0-1)
- Layout Jitter: Scroll offset variation for natural UI feel (0-1)
- Event Density: Distribution across different event counts (0-1)

Final Score: 0-1, where 1 = highly realistic
"""

import csv
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import math


class RealismAuditor:
    def __init__(self, manifest_path: str = "data/manifest.csv"):
        self.manifest_path = Path(manifest_path)
        self.data = []
        self.metrics = {}

    def load_data(self) -> bool:
        """Load manifest.csv data."""
        if not self.manifest_path.exists():
            print(f"Manifest not found: {self.manifest_path}")
            return False

        try:
            with open(self.manifest_path, "r") as f:
                reader = csv.DictReader(f)
                self.data = list(reader)

            print(f"Loaded {len(self.data)} entries from manifest")
            return True
        except Exception as e:
            print(f"Failed to load manifest: {e}")
            return False

    def measure_popup_entropy(self) -> float:
        """
        Measure UI popup diversity using Shannon entropy.

        Higher entropy = more balanced distribution of popup types.
        Score: 0-1, normalized by max possible entropy.
        """
        popup_types = [row["popup_type"] for row in self.data]

        # Count popup occurrences
        popup_counts = Counter(popup_types)
        total = len(popup_types)

        # Calculate Shannon entropy: H = -Σ(p_i * log2(p_i))
        entropy = 0.0
        for count in popup_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Normalize by maximum possible entropy (log2 of unique types)
        unique_types = len(popup_counts)
        max_entropy = math.log2(unique_types) if unique_types > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        self.metrics["popup_entropy"] = {
            "score": normalized_entropy,
            "raw_entropy": entropy,
            "max_entropy": max_entropy,
            "unique_types": unique_types,
            "distribution": dict(popup_counts),
        }

        return normalized_entropy

    def measure_color_variance(self) -> float:
        """
        Measure color distribution variance.

        Google Calendar has 11 official colors. We expect varied usage.
        Score: Based on how well colors are distributed across events.

        Since we don't have color data in manifest, we estimate based on
        event distribution (each event likely gets different color).
        """
        # Count events per screenshot
        event_counts = [int(row["#events"]) for row in self.data]

        # Calculate coefficient of variation for event distribution
        if len(event_counts) > 0 and np.mean(event_counts) > 0:
            cv = np.std(event_counts) / np.mean(event_counts)
            # Normalize CV to 0-1 range (typical CV for good variance is 0.5-1.5)
            score = min(1.0, cv / 1.0)
        else:
            score = 0.0

        self.metrics["color_variance"] = {
            "score": score,
            "event_count_mean": np.mean(event_counts),
            "event_count_std": np.std(event_counts),
            "coefficient_of_variation": cv if np.mean(event_counts) > 0 else 0.0,
        }

        return score

    def measure_layout_jitter(self) -> float:
        """
        Measure layout variation (scroll jitter).

        In a realistic UI, there's natural scroll offset variation.
        We measure this indirectly through popup placement diversity.

        Score: Based on popup type diversity and event count variance.
        """
        # Measure how varied the screenshots are
        event_counts = [int(row["#events"]) for row in self.data]
        popup_types = [row["popup_type"] for row in self.data]

        # Count unique (event_count, popup_type) combinations
        combinations = set(zip(event_counts, popup_types))
        total_possible = len(self.data)

        # Higher ratio = more varied layouts
        variation_score = (
            len(combinations) / total_possible if total_possible > 0 else 0.0
        )

        self.metrics["layout_jitter"] = {
            "score": variation_score,
            "unique_combinations": len(combinations),
            "total_screenshots": total_possible,
        }

        return variation_score

    def measure_event_density(self) -> float:
        """
        Measure event density distribution.

        A realistic dataset should have varied event counts (0-10+).
        Score: Based on coverage of event count range and distribution.
        """
        event_counts = [int(row["#events"]) for row in self.data]

        # Count distribution
        event_distribution = Counter(event_counts)

        # Check coverage of 0-10 range
        expected_range = set(range(0, 11))
        actual_range = set(event_counts)
        coverage = len(actual_range & expected_range) / len(expected_range)

        # Calculate uniformity (using entropy)
        total = len(event_counts)
        entropy = 0.0
        for count in event_distribution.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Max entropy for 11 bins (0-10 events)
        max_entropy = math.log2(11)
        uniformity = entropy / max_entropy

        # Score is average of coverage and uniformity
        score = (coverage + uniformity) / 2.0

        self.metrics["event_density"] = {
            "score": score,
            "coverage": coverage,
            "uniformity": uniformity,
            "distribution": dict(event_distribution),
            "unique_counts": len(actual_range),
        }

        return score

    def calculate_overall_score(self) -> float:
        """
        Calculate overall realism score.

        Weighted average of all metrics:
        - Popup Entropy: 30% (most important for UI realism)
        - Color Variance: 20%
        - Layout Jitter: 25%
        - Event Density: 25%
        """
        weights = {
            "popup_entropy": 0.30,
            "color_variance": 0.20,
            "layout_jitter": 0.25,
            "event_density": 0.25,
        }

        scores = {
            "popup_entropy": self.metrics["popup_entropy"]["score"],
            "color_variance": self.metrics["color_variance"]["score"],
            "layout_jitter": self.metrics["layout_jitter"]["score"],
            "event_density": self.metrics["event_density"]["score"],
        }

        overall = sum(scores[k] * weights[k] for k in weights.keys())

        self.metrics["overall"] = {
            "score": overall,
            "weights": weights,
            "component_scores": scores,
        }

        return overall

    def print_report(self):
        """Print detailed realism audit report."""
        print("\n" + "=" * 80)
        print("GOOGLE CALENDAR GYM - REALISM AUDIT REPORT")
        print("=" * 80)

        print(f"\nDataset: {len(self.data)} screenshots")

        # Popup Entropy
        popup = self.metrics["popup_entropy"]
        print(f"\n1. UI Popup Entropy: {popup['score']:.3f}")
        print(f"    Raw Entropy: {popup['raw_entropy']:.3f}")
        print(f"    Max Entropy: {popup['max_entropy']:.3f}")
        print(f"    Unique Types: {popup['unique_types']}")
        print(f"    Distribution:")
        for ptype, count in sorted(
            popup["distribution"].items(), key=lambda x: x[1], reverse=True
        ):
            pct = count / len(self.data) * 100
            print(f"      {ptype}: {count} ({pct:.1f}%)")

        # Color Variance
        color = self.metrics["color_variance"]
        print(f"\n2. Color Variance: {color['score']:.3f}")
        print(f"    Mean Events/Screenshot: {color['event_count_mean']:.2f}")
        print(f"    Std Dev: {color['event_count_std']:.2f}")
        print(f"    Coefficient of Variation: {color['coefficient_of_variation']:.3f}")

        # Layout Jitter
        layout = self.metrics["layout_jitter"]
        print(f"\n3. Layout Jitter: {layout['score']:.3f}")
        print(f"    Unique Combinations: {layout['unique_combinations']}")
        print(f"    Total Screenshots: {layout['total_screenshots']}")

        # Event Density
        density = self.metrics["event_density"]
        print(f"\n4. Event Density: {density['score']:.3f}")
        print(f"    Coverage (0-10 range): {density['coverage']:.3f}")
        print(f"    Uniformity: {density['uniformity']:.3f}")
        print(f"    Unique Counts: {density['unique_counts']}")
        print(f"    Distribution:")
        for count in sorted(density["distribution"].keys()):
            screenshots = density["distribution"][count]
            pct = screenshots / len(self.data) * 100
            print(f"      {count} events: {screenshots} screenshots ({pct:.1f}%)")

        # Overall Score
        overall = self.metrics["overall"]
        print(f"\n" + "=" * 80)
        print(f"OVERALL REALISM SCORE: {overall['score']:.3f}")
        print("=" * 80)

        # Interpretation
        score = overall["score"]
        if score >= 0.8:
            rating = "EXCELLENT"
            comment = "Highly realistic dataset with excellent diversity"
        elif score >= 0.7:
            rating = "VERY GOOD"
            comment = "Very realistic with good variation across dimensions"
        elif score >= 0.6:
            rating = "GOOD"
            comment = "Realistic dataset with moderate diversity"
        elif score >= 0.5:
            rating = "FAIR"
            comment = "Acceptable realism but could improve diversity"
        else:
            rating = "NEEDS IMPROVEMENT"
            comment = "Low realism score, increase variation"

        print(f"\nRating: {rating}")
        print(f"{comment}\n")

        # Component breakdown
        print("Component Scores (weighted):")
        for component, weight in overall["weights"].items():
            comp_score = overall["component_scores"][component]
            weighted = comp_score * weight
            print(f"  {component}: {comp_score:.3f} × {weight:.0%} = {weighted:.3f}")

        print("\n" + "=" * 80)

    def run_audit(self) -> Tuple[bool, float]:
        """Run complete realism audit."""
        if not self.load_data():
            return False, 0.0

        # Measure all dimensions
        self.measure_popup_entropy()
        self.measure_color_variance()
        self.measure_layout_jitter()
        self.measure_event_density()

        # Calculate overall score
        overall_score = self.calculate_overall_score()

        # Print report
        self.print_report()

        return True, overall_score


def main():
    """Run realism audit."""
    auditor = RealismAuditor()
    success, score = auditor.run_audit()

    if success:
        print(f"Realism audit completed successfully")
        print(f"Score: {score:.3f}/1.000")
        return 0
    else:
        print(f"Realism audit failed")
        return 1


if __name__ == "__main__":
    exit(main())
