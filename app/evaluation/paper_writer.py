import csv
import re
from pathlib import Path
from typing import Any


RESULTS_DIR = Path(__file__).parent / "results"
PAPER_PATH = Path("EDMIE_Full_Paper.md")


def _read_rows(csv_path: str | Path) -> list[dict[str, Any]]:
    with Path(csv_path).open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _metric(rows: list[dict[str, Any]], mode: str, key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        if row.get("ablation_mode") != mode:
            continue
        try:
            values.append(float(row.get(key, "")))
        except (TypeError, ValueError):
            continue
    return values


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _extract_p_values(summary: str) -> dict[str, float]:
    p_values = [float(value) for value in re.findall(r"p-value=([0-9.eE+-]+)", summary)]
    return {
        "turns_full_vs_no_ucb": p_values[0] if len(p_values) >= 1 else 1.0,
        "mae_full_vs_no_tracker": p_values[1] if len(p_values) >= 2 else 1.0,
    }


def summarize_results(
    csv_path: str | Path = RESULTS_DIR / "ablation_results.csv",
    summary_path: str | Path = RESULTS_DIR / "statistical_summary.txt",
) -> dict[str, float]:
    rows = _read_rows(csv_path)
    summary = Path(summary_path).read_text(encoding="utf-8")
    p_values = _extract_p_values(summary)
    full_turns = _mean(_metric(rows, "full", "negotiation_turns"))
    no_ucb_turns = _mean(_metric(rows, "no_ucb", "negotiation_turns"))
    no_tracker_turns = _mean(_metric(rows, "no_tracker", "negotiation_turns"))
    full_mae = _mean(_metric(rows, "full", "mae_error"))
    no_ucb_mae = _mean(_metric(rows, "no_ucb", "mae_error"))
    no_tracker_mae = _mean(_metric(rows, "no_tracker", "mae_error"))
    turn_reduction = (
        ((no_ucb_turns - full_turns) / no_ucb_turns) * 100.0 if no_ucb_turns else 0.0
    )
    mae_reduction = (
        ((no_tracker_mae - full_mae) / no_tracker_mae) * 100.0
        if no_tracker_mae
        else 0.0
    )
    return {
        "full_turns": full_turns,
        "no_ucb_turns": no_ucb_turns,
        "no_tracker_turns": no_tracker_turns,
        "full_mae": full_mae,
        "no_ucb_mae": no_ucb_mae,
        "no_tracker_mae": no_tracker_mae,
        "turn_reduction": turn_reduction,
        "mae_reduction": mae_reduction,
        **p_values,
    }


def _case_excerpt(case_text: str) -> dict[str, str]:
    labels = {
        "initial": "Initial Query | User",
        "probe": "Round 1 | Agent Pareto Probe",
        "feedback": "Round 1 | Simulator Feedback",
        "final": "Final | EDMIE XAI Recommendation",
    }
    excerpts: dict[str, str] = {}
    for key, label in labels.items():
        pattern = re.escape(f"**[{label}]**") + r':\s*"([^"]+)"'
        match = re.search(pattern, case_text)
        excerpts[key] = match.group(1) if match else ""
    return excerpts


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def generate_paper(
    output_path: str | Path = PAPER_PATH,
    results_dir: str | Path = RESULTS_DIR,
) -> str:
    results = Path(results_dir)
    metrics = summarize_results(
        results / "ablation_results.csv",
        results / "statistical_summary.txt",
    )
    summary_text = (results / "statistical_summary.txt").read_text(encoding="utf-8")
    case_text = (results / "case_study.md").read_text(encoding="utf-8")
    case = _case_excerpt(case_text)
    turns_p = metrics["turns_full_vs_no_ucb"]
    mae_p = metrics["mae_full_vs_no_tracker"]
    paper = f"""# EDMIE: Evidence-Driven Mixed-Initiative Elicitation for High-Stakes Preference Discovery

## Abstract

High-stakes advisory systems often fail not because they lack retrieval capacity, but because users strategically hide their real constraints. In college-admission planning, a candidate may announce a defensive surface preference such as prestige or geography while privately holding a bottom line about major fit, tuition, or family constraints. We present **EDMIE**, an Evidence-Driven Mixed-Initiative Elicitation Agent that couples deterministic SQL evidence, non-compensatory multi-attribute utility, UCB-guided active probing, and Bradley-Terry posterior tracking. In our Iceberg Profile Sandbox, EDMIE achieved a mean negotiation cost of {_fmt(metrics["full_turns"])} turns versus {_fmt(metrics["no_ucb_turns"])} turns without UCB active probing, a {_fmt(metrics["turn_reduction"], 1)}% reduction (Welch t-test p-value={turns_p:.3g}). It also reduced preference-alignment MAE to {_fmt(metrics["full_mae"])} compared with {_fmt(metrics["no_tracker_mae"])} without the BT-gradient tracker, a {_fmt(metrics["mae_reduction"], 1)}% reduction (p-value={mae_p:.3g}). These findings indicate that mathematically constrained mixed-initiative elicitation can convert hidden, defensive preference states into auditable recommendation policies.

## 1. Introduction

Conventional tool-augmented recommendation agents still behave like passive retrieval systems: the user states constraints, the system queries a database, and a language model verbalizes the returned rows. This workflow is brittle in high-risk domains because users frequently express defensive or socially desirable constraints rather than their true bottom lines. In gaokao volunteer planning, for example, an applicant may say "I only want a top school" while privately caring most about computer-science major continuity; another may ask for "high value" while refusing to leave the home province. A passive Tool AI cannot distinguish surface rhetoric from latent utility.

EDMIE reframes the interaction as collaborative AI. Instead of treating the first query as ground truth, it constructs evidence-backed Pareto contrasts and asks the user to choose between marginal substitutions. The agent therefore acts as a cognitive scaffold: it exposes trade-offs that the user could not or would not articulate initially. Crucially, EDMIE never lets an LLM invent factual candidates. Every candidate comes from deterministic PostgreSQL probes, while the LLM is restricted to planning, questioning, and explanation.

Our central claim is that preference elicitation should be both mixed-initiative and mathematically disciplined. Mixed initiative supplies the interactional pressure needed to reveal hidden bottom lines; mathematical discipline prevents the system from falling into linear compensation traps, such as ranking an unaffordable elite program above a feasible option merely because school prestige dominates an additive score.

## 2. Methodology

### 2.1 Non-compensatory SAVF and Local Min-Max Normalization

EDMIE maps each SQL candidate \(x\) into a single-attribute value vector:

$$
\\Phi(x) = [\\phi_{{school}}(x), \\phi_{{major}}(x), \\phi_{{tuition}}(x), \\phi_{{quality}}(x), \\phi_{{geo}}(x)].
$$

School prestige is represented by a tiered step function. Major and geography use ontology-distance penalties. Continuous quality is normalized locally within the candidate pool:

$$
\\phi_{{quality}}(x_i)=\\frac{{q_i-Q_{{min}}}}{{Q_{{max}}-Q_{{min}}}},
$$

with a neutral value when the pool has no variance. Tuition is non-compensatory:

$$
\\phi_{{tuition}}(x)=
\\begin{{cases}}
1, & tuition(x) \\le budget,\\\\
1-2\\cdot \\frac{{tuition(x)-budget}}{{budget}}, & 0 < \\frac{{tuition(x)-budget}}{{budget}} < 0.30,\\\\
-9999, & \\frac{{tuition(x)-budget}}{{budget}} \\ge 0.30.
\\end{{cases}}
$$

The final implicit utility is:

$$
U(x)=\\sum_k w_k\\phi_k(x).
$$

This design explicitly blocks severe budget violations from being rescued by prestige or quality.

### 2.2 Max-EIG Probing via UCB

EDMIE maintains a belief state over preference weights and uncertainty. Radar planning computes a UCB-style active-learning score:

$$
UCB_k = w_k + \\lambda\\sqrt{{\\sigma_k^2}},
$$

where \(\\lambda=1.5\). The dimension with the largest UCB score is mapped to a deterministic SQL probe. The LLM planner receives a system-level instruction requiring that probe; a Python sanitizer enforces the decision even if the LLM drifts. For conversational pressure, EDMIE selects the top-utility candidate \(A\) and the maximum-divergence candidate \(B\) within the top candidate set:

$$
B^*=\\arg\\max_{{B\\in TopK}} \\|\\Phi(B)-\\Phi(A)\\|_1.
$$

The resulting question asks the user whether they will sacrifice a cost dimension to obtain a gain dimension.

### 2.3 Posterior Tracking via Bradley-Terry and D-S Theory

When the user accepts or rejects a proposed trade-off, EDMIE interprets the response through a Bradley-Terry random-utility model. Let

$$
\\Delta \\Phi = \\Phi(B)-\\Phi(A), \\quad
\\Delta U = \\sum_k w_k\\Delta\\phi_k.
$$

The predicted probability that the user chooses \(B\) is:

$$
P(B)=\\frac{{1}}{{1+\\exp(-\\tau\\Delta U)}}, \\quad \\tau=3.
$$

For observed label \(Y\\in\\{{0,1\\}}\), weights are updated by logistic gradient ascent:

$$
w_k' = w_k + \\eta (Y-P(B))\\Delta\\phi_k, \\quad \\eta=0.3.
$$

Weights are clipped and renormalized. For hesitant or ambiguous feedback, EDMIE applies a Dempster-Shafer inspired ignorance update: it leaves the mean unchanged but increases variance,

$$
\\sigma_k^2 \\leftarrow \\min(1, 1.2\\sigma_k^2),
$$

forcing subsequent turns to seek information rather than hallucinating certainty.

## 3. System Architecture

EDMIE is implemented as a LangGraph state machine with a suspend/resume micro-loop. The radar node plans and executes deterministic probes; the negotiator node either interrupts with a Pareto question or emits a final recommendation; the preference tracker updates the belief state and routes back to radar. The `interrupt()` call freezes the graph at the exact conversational boundary. `Command(resume=...)` wakes the graph below the suspension point, so semantic normalization and gatekeeping do not rerun. This provides a clean temporal separation between exploration and exploitation.

The final exploitation phase uses a global baseline probe that ranks the hard-feasible candidate pool by implicit utility and organizes recommendations into Reach, Match, and Safety buckets. The final report therefore explains inferred preferences before displaying the volunteer list.

## 4. Experiments and Results

### 4.1 Iceberg Profile Sandbox

We evaluate EDMIE in an Iceberg Profile Sandbox. Each profile contains a visible defensive query, a hidden bottom line, and ground-truth preference weights. A simulator answers agent questions according to hidden constraints. The benchmark compares three variants: EDMIE (full), w/o UCB Active Probing, and w/o BT-Gradient Tracker.

### 4.2 Quantitative Results

Figure 1 reports convergence efficiency: `app/evaluation/results/fig_efficiency_turns.png`. EDMIE required {_fmt(metrics["full_turns"])} turns on average, while the no-UCB variant required {_fmt(metrics["no_ucb_turns"])} turns. This is a {_fmt(metrics["turn_reduction"], 1)}% reduction in interaction cost, with p-value={turns_p:.3g}.

Figure 2 reports alignment error: `app/evaluation/results/fig_alignment_mae.png`. EDMIE reached MAE={_fmt(metrics["full_mae"])}; removing the BT-gradient tracker increased MAE to {_fmt(metrics["no_tracker_mae"])}. The relative reduction is {_fmt(metrics["mae_reduction"], 1)}%, with p-value={mae_p:.3g}. The raw statistical summary is reproduced below:

```text
{summary_text.strip()}
```

The two figures are also available as PDF artifacts: `app/evaluation/results/fig_efficiency_turns.pdf` and `app/evaluation/results/fig_alignment_mae.pdf`.

### 4.3 Qualitative Case Study

The exported case study shows how EDMIE exposes hidden bottom lines by forcing a high-contrast choice. The user begins with:

> {case.get("initial") or "N/A"}

The agent then issues a Pareto probe:

> {case.get("probe") or "N/A"}

The simulator's reply reveals the hidden utility:

> {case.get("feedback") or "N/A"}

Finally, EDMIE explains the inferred preference model:

> {case.get("final") or "N/A"}

This micro-transcript illustrates the central mechanism: the agent does not ask open-ended preference questions. It constructs a marginal substitution that makes a hidden constraint behaviorally observable.

## 5. Discussion

The ablation pattern supports the design hypothesis. UCB is not merely a planner hint; it reduces conversational wandering by selecting the dimension with the highest expected information gain. The BT tracker is equally important: without gradient updates on observed choices, the system cannot convert feedback into calibrated utility weights. The non-compensatory tuition guardrail prevents pathological recommendations even when other attributes are strong.

## 6. Conclusion

EDMIE demonstrates a path from passive Tool AI to collaborative, evidence-grounded elicitation. By combining deterministic probes, non-compensatory MAUT, UCB-driven Pareto questioning, and Bradley-Terry posterior tracking, it uncovers hidden bottom lines while keeping factual candidates auditable. The generated benchmark artifacts and paper-ready figures provide a reproducible foundation for further evaluation in real admissions-advising deployments.
"""
    Path(output_path).write_text(paper, encoding="utf-8")
    return str(output_path)


def validate_paper(
    path: str | Path = PAPER_PATH, results_dir: str | Path = RESULTS_DIR
) -> None:
    paper_path = Path(path)
    if not paper_path.exists():
        raise FileNotFoundError(str(paper_path))
    text = paper_path.read_text(encoding="utf-8")
    forbidden = ("XXX", "p-value here", "TODO")
    missing = [item for item in forbidden if item in text]
    if missing:
        raise ValueError(f"paper contains placeholders: {missing}")
    required = [
        "app/evaluation/results/fig_efficiency_turns.png",
        "app/evaluation/results/fig_alignment_mae.png",
        "p-value=",
        "$$",
        "Abstract",
        "Methodology",
        "Experiments and Results",
    ]
    absent = [item for item in required if item not in text]
    if absent:
        raise ValueError(f"paper missing required content: {absent}")
    for artifact in (
        "ablation_results.csv",
        "statistical_summary.txt",
        "fig_efficiency_turns.png",
        "fig_efficiency_turns.pdf",
        "fig_alignment_mae.png",
        "fig_alignment_mae.pdf",
        "case_study.md",
    ):
        if not (Path(results_dir) / artifact).exists():
            raise FileNotFoundError(str(Path(results_dir) / artifact))


def run_cli() -> str:
    path = generate_paper()
    validate_paper(path)
    print(f"[paper_writer] wrote {path}")
    return path


if __name__ == "__main__":
    run_cli()
