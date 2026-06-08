import argparse
import json
from pathlib import Path

from .capabilities import capability_plan_from_pipeline
from .context import create_run, load_run
from .io import read_yaml
from .pipeline import advance_pipeline, initialize_pipeline_run, status_summary, validate_pipeline
from .project import find_project_root
from .stages import approve_gate, generate_voice, initialize_run_files, package, qa, render


def command_new(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = create_run(root, run_id=args.run_id, overwrite=args.overwrite)
    initialize_run_files(ctx, template=args.template)
    print(ctx.run_dir.relative_to(root))


def command_approve(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    approve_gate(ctx, args.gate, summary=args.summary)
    print(f"approved {args.gate}: {ctx.run_dir.relative_to(root)}")


def command_run(args: argparse.Namespace) -> None:
    root = find_project_root()
    if args.pipeline:
        pipeline_path = Path(args.pipeline)
        if not pipeline_path.is_absolute():
            pipeline_path = root / pipeline_path
        ctx = create_run(root, run_id=args.run_id, overwrite=args.overwrite)
        initialize_pipeline_run(ctx, pipeline_path)
    else:
        ctx = load_run(root, args.run)

    result = advance_pipeline(ctx)
    print(result["message"])
    print(result["run"])
    if result["next_action"]:
        print(result["next_action"])


def command_status(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    summary = status_summary(ctx)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    state = summary["state"]
    print(f"run: {summary['run']}")
    print(f"status: {state.get('status', '')}")
    print(f"current_stage: {state.get('current_stage', '')}")
    if state.get("next_action"):
        print(f"next_action: {state['next_action']}")
    print("approvals:")
    for gate, status in summary["approvals"].items():
        print(f"  {gate}: {status}")
    print(f"artifacts: {summary['artifact_count']}")


def command_validate(args: argparse.Namespace) -> None:
    root = find_project_root()
    pipeline_path = Path(args.pipeline)
    if not pipeline_path.is_absolute():
        pipeline_path = root / pipeline_path

    pipeline = read_yaml(pipeline_path)
    errors = ["pipeline is empty"] if not pipeline else validate_pipeline(pipeline)
    if args.json:
        print(json.dumps({"pipeline": str(Path(args.pipeline)), "valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    elif errors:
        print("pipeline invalid")
        for error in errors:
            print(f"- {error}")
    else:
        print("pipeline valid")

    if errors:
        raise SystemExit(1)


def command_capabilities(args: argparse.Namespace) -> None:
    root = find_project_root()
    if args.pipeline:
        pipeline_path = Path(args.pipeline)
        if not pipeline_path.is_absolute():
            pipeline_path = root / pipeline_path
        pipeline = read_yaml(pipeline_path)
    else:
        ctx = load_run(root, args.run)
        pipeline = read_yaml(ctx.path("pipeline.yml"))

    plan = capability_plan_from_pipeline(pipeline)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    print("capability dry-run")
    print(f"mode: {plan['mode']}")
    required = ", ".join(plan["required"]) if plan["required"] else "none"
    print(f"required: {required}")
    for item in plan["capabilities"]:
        marker = "required" if item["required"] else "optional"
        print(f"- {item['name']}: {marker}, {item['status']}, {item['action']}")
    browser_preflight = plan.get("browser_preflight", {})
    if browser_preflight.get("enabled"):
        print("browser_preflight:")
        print(f"  status: {browser_preflight['status']}")
        print(f"  target_url: {browser_preflight['target_url']}")
        print(f"  target_kind: {browser_preflight['target_kind']}")
        print(f"  recording: {browser_preflight['recording']['enabled']}")


def command_voice(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    generate_voice(ctx)
    print(ctx.path("audio/narration.mp3").relative_to(root))


def command_render(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    render(ctx)
    print(ctx.path("render/final_16x9.mp4").relative_to(root))


def command_qa(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    qa(ctx)
    print(ctx.path("qa/report.md").relative_to(root))


def command_package(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    package(ctx)
    print(ctx.path("package").relative_to(root))


def command_run_demo(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = create_run(root, run_id=args.run_id, overwrite=args.overwrite)
    initialize_run_files(ctx, template="general_demo")
    approve_gate(ctx, "brief")
    approve_gate(ctx, "plan")
    approve_gate(ctx, "execution")
    generate_voice(ctx)
    render(ctx)
    qa(ctx)
    package(ctx)
    print(ctx.run_dir.relative_to(root))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-video-maker")
    sub = parser.add_subparsers(required=True)

    new_parser = sub.add_parser("new", help="create a new run")
    new_parser.add_argument("--template", default="general_demo")
    new_parser.add_argument("--run-id")
    new_parser.add_argument("--overwrite", action="store_true")
    new_parser.set_defaults(func=command_new)

    approve_parser = sub.add_parser("approve", help="record an approval gate")
    approve_parser.add_argument("--run", required=True)
    approve_parser.add_argument("--gate", required=True, choices=["brief", "plan", "execution", "upload", "publish"])
    approve_parser.add_argument("--summary", default="approved")
    approve_parser.set_defaults(func=command_approve)

    run_parser = sub.add_parser("run", help="create or continue a pipeline run")
    run_target = run_parser.add_mutually_exclusive_group(required=True)
    run_target.add_argument("--pipeline")
    run_target.add_argument("--run")
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--overwrite", action="store_true")
    run_parser.set_defaults(func=command_run)

    status_parser = sub.add_parser("status", help="show run state, approvals, and artifacts")
    status_parser.add_argument("--run", required=True)
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(func=command_status)

    validate_parser = sub.add_parser("validate", help="validate a pipeline file")
    validate_parser.add_argument("--pipeline", required=True)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=command_validate)

    capabilities_parser = sub.add_parser("capabilities", help="show capability adapter dry-run plan")
    capabilities_target = capabilities_parser.add_mutually_exclusive_group(required=True)
    capabilities_target.add_argument("--pipeline")
    capabilities_target.add_argument("--run")
    capabilities_parser.add_argument("--json", action="store_true")
    capabilities_parser.set_defaults(func=command_capabilities)

    voice_parser = sub.add_parser("voice", help="generate narration audio and subtitles")
    voice_parser.add_argument("--run", required=True)
    voice_parser.set_defaults(func=command_voice)

    render_parser = sub.add_parser("render", help="render final 16:9 video")
    render_parser.add_argument("--run", required=True)
    render_parser.set_defaults(func=command_render)

    qa_parser = sub.add_parser("qa", help="run video QA checks")
    qa_parser.add_argument("--run", required=True)
    qa_parser.set_defaults(func=command_qa)

    package_parser = sub.add_parser("package", help="create upload package")
    package_parser.add_argument("--run", required=True)
    package_parser.set_defaults(func=command_package)

    demo_parser = sub.add_parser("run-demo", help="run the full P0 self-intro demo")
    demo_parser.add_argument("--run-id", default="p0-self-intro")
    demo_parser.add_argument("--overwrite", action="store_true")
    demo_parser.set_defaults(func=command_run_demo)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
