import argparse
import json
from pathlib import Path

from .browser_adapter import record_browser_preflight_result
from .browser_capture_workflow import generate_browser_capture
from .capabilities import capability_plan_from_pipeline
from .context import create_run, load_run
from .edit_render_workflow import generate_edit_render
from .io import read_yaml
from .pipeline import advance_pipeline, initialize_pipeline_run, status_summary, validate_pipeline
from .project import find_project_root
from .publish_package_workflow import generate_publish_package
from .qa_revision_workflow import generate_qa_revision
from .script_workflow import generate_video_script
from .stages import approve_gate, generate_voice, initialize_run_files, package, qa, render
from .voice_subtitle_workflow import generate_voice_subtitle


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


def command_browser_result(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    screenshot = Path(args.screenshot)
    if not screenshot.is_absolute():
        screenshot = root / screenshot
    result = record_browser_preflight_result(
        ctx,
        screenshot=screenshot,
        current_url=args.url,
        title=args.title,
        non_blank=args.non_blank,
    )
    print(f"browser preflight {result['status']}: {ctx.run_dir.relative_to(root)}")


def command_voice(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    generate_voice(ctx)
    print(ctx.path("audio/narration.mp3").relative_to(root))


def command_voice_subtitle(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_voice_subtitle(ctx)
    print(f"voice-subtitle {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next skill: {handoff['next_skill_suggestion']}")


def command_script(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_video_script(ctx)
    print(f"video-script {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next skill: {handoff['next_skill_suggestion']}")


def command_render(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    render(ctx)
    print(ctx.path("render/final_16x9.mp4").relative_to(root))


def command_edit_render(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_edit_render(ctx)
    print(f"edit-render {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next skill: {handoff['next_skill_suggestion']}")


def command_browser_capture(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_browser_capture(ctx)
    print(f"browser-capture {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next skill: {handoff['next_skill_suggestion']}")


def command_qa_revision(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_qa_revision(ctx)
    print(f"qa-revision {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next skill: {handoff['next_skill_suggestion']}")


def command_publish_package(args: argparse.Namespace) -> None:
    root = find_project_root()
    ctx = load_run(root, args.run)
    handoff = generate_publish_package(ctx)
    print(f"publish-package {handoff['status']}: {ctx.run_dir.relative_to(root)}")
    print(f"next gate: {handoff['next_gate']}")


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

    browser_result_parser = sub.add_parser("browser-result", help="record Browser preflight result after execution approval")
    browser_result_parser.add_argument("--run", required=True)
    browser_result_parser.add_argument("--screenshot", required=True)
    browser_result_parser.add_argument("--url", required=True)
    browser_result_parser.add_argument("--title", required=True)
    browser_result_parser.add_argument("--non-blank", action="store_true")
    browser_result_parser.set_defaults(func=command_browser_result)

    script_parser = sub.add_parser("script", help="generate video-script outputs after plan approval")
    script_parser.add_argument("--run", required=True)
    script_parser.set_defaults(func=command_script)

    voice_parser = sub.add_parser("voice", help="generate narration audio and subtitles")
    voice_parser.add_argument("--run", required=True)
    voice_parser.set_defaults(func=command_voice)

    voice_subtitle_parser = sub.add_parser("voice-subtitle", help="generate voice-subtitle outputs after video-script review")
    voice_subtitle_parser.add_argument("--run", required=True)
    voice_subtitle_parser.set_defaults(func=command_voice_subtitle)

    render_parser = sub.add_parser("render", help="render final 16:9 video")
    render_parser.add_argument("--run", required=True)
    render_parser.set_defaults(func=command_render)

    edit_render_parser = sub.add_parser("edit-render", help="generate edit-render outputs after voice-subtitle review")
    edit_render_parser.add_argument("--run", required=True)
    edit_render_parser.set_defaults(func=command_edit_render)

    browser_capture_parser = sub.add_parser("browser-capture", help="capture browser screenshot and recording after execution approval")
    browser_capture_parser.add_argument("--run", required=True)
    browser_capture_parser.set_defaults(func=command_browser_capture)

    qa_revision_parser = sub.add_parser("qa-revision", help="run QA checks after edit-render")
    qa_revision_parser.add_argument("--run", required=True)
    qa_revision_parser.set_defaults(func=command_qa_revision)

    publish_package_parser = sub.add_parser("publish-package", help="create publishing package after QA")
    publish_package_parser.add_argument("--run", required=True)
    publish_package_parser.set_defaults(func=command_publish_package)

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
