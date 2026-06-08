import argparse
from pathlib import Path

from .context import create_run, load_run
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
    approve_gate(ctx, args.gate)
    print(f"approved {args.gate}: {ctx.run_dir.relative_to(root)}")


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
    approve_parser.set_defaults(func=command_approve)

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
