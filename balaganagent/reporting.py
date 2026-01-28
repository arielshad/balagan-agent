"""Report generation for chaos experiments."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .experiment import ExperimentResult


@dataclass
class ReportSection:
    """A section of the report."""

    title: str
    content: dict[str, Any]
    severity: str = "info"  # info, warning, critical


class ReportGenerator:
    """
    Generates comprehensive reports from chaos experiment results.

    Supports multiple output formats:
    - JSON
    - Markdown
    - HTML
    - Terminal (colored output)
    """

    def __init__(self):
        self._sections: list[ReportSection] = []

    def add_section(self, title: str, content: dict[str, Any], severity: str = "info"):
        """Add a section to the report."""
        self._sections.append(ReportSection(title, content, severity))

    def generate_from_results(
        self,
        results: list[ExperimentResult],
        aggregate_metrics: Optional[dict[str, Any]] = None,
        reliability_report: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate a report from experiment results."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self._generate_summary(results, aggregate_metrics),
            "experiments": [r.to_dict() for r in results],
            "reliability": reliability_report or {},
            "recommendations": self._generate_recommendations(results, reliability_report),
        }

        return report

    def _generate_summary(
        self,
        results: list[ExperimentResult],
        aggregate_metrics: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate summary section."""
        total = len(results)
        completed = sum(1 for r in results if r.status.value == "completed")
        failed = sum(1 for r in results if r.status.value == "failed")
        aborted = sum(1 for r in results if r.status.value == "aborted")

        total_ops = sum(r.total_operations for r in results)
        successful_ops = sum(r.successful_operations for r in results)
        total_faults = sum(r.faults_injected for r in results)

        summary = {
            "total_experiments": total,
            "completed": completed,
            "failed": failed,
            "aborted": aborted,
            "total_operations": total_ops,
            "successful_operations": successful_ops,
            "overall_success_rate": successful_ops / total_ops if total_ops > 0 else 0,
            "total_faults_injected": total_faults,
        }

        if aggregate_metrics:
            summary["aggregate_metrics"] = aggregate_metrics

        return summary

    def _generate_recommendations(
        self,
        results: list[ExperimentResult],
        reliability_report: Optional[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on results."""
        recommendations = []

        # Analyze success rates
        total_ops = sum(r.total_operations for r in results)
        successful_ops = sum(r.successful_operations for r in results)
        success_rate = successful_ops / total_ops if total_ops > 0 else 0

        if success_rate < 0.9:
            recommendations.append(
                f"Overall success rate is {success_rate:.1%}. "
                "Consider implementing more robust error handling and retry logic."
            )

        # Analyze recovery rates
        recovered = sum(r.recovered_operations for r in results)
        failed = sum(r.failed_operations for r in results)
        recovery_rate = recovered / failed if failed > 0 else 1.0

        if recovery_rate < 0.8:
            recommendations.append(
                f"Recovery rate is {recovery_rate:.1%}. "
                "Agents should implement better recovery mechanisms."
            )

        # Analyze fault types
        fault_counts: dict[str, int] = {}
        for result in results:
            for fault_type, count in result.faults_by_type.items():
                fault_counts[fault_type] = fault_counts.get(fault_type, 0) + count

        # Find most impactful fault types
        if fault_counts:
            most_common = max(fault_counts, key=fault_counts.get)  # type: ignore
            recommendations.append(
                f"Most frequent fault type: {most_common}. "
                "Focus testing and hardening on this failure mode."
            )

        # Add reliability-based recommendations
        if reliability_report and "recommendations" in reliability_report:
            recommendations.extend(reliability_report["recommendations"])

        if not recommendations:
            recommendations.append("All metrics within acceptable ranges. Continue monitoring.")

        return recommendations

    def to_json(self, report: dict[str, Any], indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(report, indent=indent, default=str)

    def to_markdown(self, report: dict[str, Any]) -> str:
        """Convert report to Markdown format."""
        lines = [
            "# BalaganAgent Experiment Report",
            "",
            f"**Generated:** {report['generated_at']}",
            "",
            "## Summary",
            "",
        ]

        summary = report["summary"]
        lines.extend(
            [
                f"- **Total Experiments:** {summary['total_experiments']}",
                f"- **Completed:** {summary['completed']}",
                f"- **Failed:** {summary['failed']}",
                f"- **Aborted:** {summary['aborted']}",
                f"- **Total Operations:** {summary['total_operations']}",
                f"- **Success Rate:** {summary['overall_success_rate']:.1%}",
                f"- **Faults Injected:** {summary['total_faults_injected']}",
                "",
            ]
        )

        # Reliability section
        if report.get("reliability"):
            reliability = report["reliability"]
            lines.extend(
                [
                    "## Reliability Metrics",
                    "",
                    f"- **Overall Score:** {reliability.get('overall_score', 'N/A')}",
                    f"- **Grade:** {reliability.get('grade', 'N/A')}",
                    f"- **Availability:** {reliability.get('availability', 'N/A')}",
                    f"- **MTTR:** {reliability.get('mttr_seconds', 'N/A')}s",
                    "",
                ]
            )

        # Experiments section
        lines.extend(
            [
                "## Experiments",
                "",
            ]
        )

        for exp in report["experiments"]:
            config = exp["config"]
            lines.extend(
                [
                    f"### {config['name']}",
                    "",
                    f"- **Status:** {exp['status']}",
                    f"- **Duration:** {exp['duration_seconds']:.2f}s",
                    f"- **Operations:** {exp['total_operations']}",
                    f"- **Success Rate:** {exp['success_rate']:.1%}",
                    f"- **Recovery Rate:** {exp['recovery_rate']:.1%}",
                    "",
                ]
            )

            if exp["faults_by_type"]:
                lines.append("**Faults Injected:**")
                for fault_type, count in exp["faults_by_type"].items():
                    lines.append(f"  - {fault_type}: {count}")
                lines.append("")

        # Recommendations
        lines.extend(
            [
                "## Recommendations",
                "",
            ]
        )
        for i, rec in enumerate(report["recommendations"], 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    def to_html(self, report: dict[str, Any]) -> str:
        """Convert report to HTML format."""
        summary = report["summary"]
        success_rate = summary["overall_success_rate"]

        # Determine status color
        if success_rate >= 0.95:
            status_color = "#28a745"  # Green
            status_text = "Healthy"
        elif success_rate >= 0.8:
            status_color = "#ffc107"  # Yellow
            status_text = "Warning"
        else:
            status_color = "#dc3545"  # Red
            status_text = "Critical"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>BalaganAgent Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; background: {status_color}; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; min-width: 150px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .experiment {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
        .recommendation {{ background: #fff3cd; padding: 10px 15px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>BalaganAgent Experiment Report</h1>
        <p>Generated: {report['generated_at']}</p>
        <p>Status: <span class="status-badge">{status_text}</span></p>

        <h2>Summary</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{summary['total_experiments']}</div>
                <div class="metric-label">Experiments</div>
            </div>
            <div class="metric">
                <div class="metric-value">{success_rate:.1%}</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary['total_operations']}</div>
                <div class="metric-label">Operations</div>
            </div>
            <div class="metric">
                <div class="metric-value">{summary['total_faults_injected']}</div>
                <div class="metric-label">Faults Injected</div>
            </div>
        </div>

        <h2>Experiments</h2>
"""

        for exp in report["experiments"]:
            config = exp["config"]
            html += f"""
        <div class="experiment">
            <h3>{config['name']}</h3>
            <table>
                <tr><td>Status</td><td>{exp['status']}</td></tr>
                <tr><td>Duration</td><td>{exp['duration_seconds']:.2f}s</td></tr>
                <tr><td>Operations</td><td>{exp['total_operations']}</td></tr>
                <tr><td>Success Rate</td><td>{exp['success_rate']:.1%}</td></tr>
                <tr><td>Recovery Rate</td><td>{exp['recovery_rate']:.1%}</td></tr>
            </table>
        </div>
"""

        html += """
        <h2>Recommendations</h2>
"""
        for rec in report["recommendations"]:
            html += f'        <div class="recommendation">{rec}</div>\n'

        html += """
    </div>
</body>
</html>"""

        return html

    def to_terminal(self, report: dict[str, Any]) -> str:
        """Convert report to terminal-friendly format with colors."""
        # ANSI color codes
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RED = "\033[91m"
        BLUE = "\033[94m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        summary = report["summary"]
        success_rate = summary["overall_success_rate"]

        # Determine status
        if success_rate >= 0.95:
            status = f"{GREEN}HEALTHY{RESET}"
        elif success_rate >= 0.8:
            status = f"{YELLOW}WARNING{RESET}"
        else:
            status = f"{RED}CRITICAL{RESET}"

        lines = [
            "",
            f"{BOLD}{'='*60}{RESET}",
            f"{BOLD}  BALAGANAGENT EXPERIMENT REPORT{RESET}",
            f"{'='*60}",
            "",
            f"  Generated: {report['generated_at']}",
            f"  Status: {status}",
            "",
            f"{BOLD}SUMMARY{RESET}",
            f"  Experiments: {summary['total_experiments']} (Completed: {summary['completed']}, Failed: {summary['failed']})",
            f"  Operations:  {summary['total_operations']} (Success Rate: {success_rate:.1%})",
            f"  Faults:      {summary['total_faults_injected']} injected",
            "",
        ]

        # Reliability
        if report.get("reliability"):
            rel = report["reliability"]
            lines.extend(
                [
                    f"{BOLD}RELIABILITY{RESET}",
                    f"  Score: {rel.get('overall_score', 'N/A')}",
                    f"  Grade: {rel.get('grade', 'N/A')}",
                    f"  MTTR:  {rel.get('mttr_seconds', 'N/A')}s",
                    "",
                ]
            )

        # Experiments
        lines.append(f"{BOLD}EXPERIMENTS{RESET}")
        for exp in report["experiments"]:
            config = exp["config"]
            exp_status = exp["status"]
            if exp_status == "completed":
                status_str = f"{GREEN}{exp_status}{RESET}"
            elif exp_status == "failed":
                status_str = f"{RED}{exp_status}{RESET}"
            else:
                status_str = f"{YELLOW}{exp_status}{RESET}"

            lines.append(f"  {BLUE}{config['name']}{RESET} [{status_str}]")
            lines.append(
                f"    Duration: {exp['duration_seconds']:.2f}s | Success: {exp['success_rate']:.1%} | Recovery: {exp['recovery_rate']:.1%}"
            )

        lines.append("")

        # Recommendations
        lines.append(f"{BOLD}RECOMMENDATIONS{RESET}")
        for i, rec in enumerate(report["recommendations"], 1):
            lines.append(f"  {i}. {rec}")

        lines.extend(["", f"{'='*60}", ""])

        return "\n".join(lines)

    def save(
        self,
        report: dict[str, Any],
        path: str,
        format: str = "json",
    ):
        """Save report to file."""
        path_obj = Path(path)

        if format == "json":
            content = self.to_json(report)
        elif format == "markdown" or format == "md":
            content = self.to_markdown(report)
        elif format == "html":
            content = self.to_html(report)
        else:
            raise ValueError(f"Unknown format: {format}")

        path_obj.write_text(content)
