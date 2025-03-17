#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import argparse


def run_command(cmd):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {cmd}", file=sys.stderr)
        print(f"Error details: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def get_commits_between_refs(start_ref, end_ref, file_path):
    """Get all commits that modified the specified file between two git references (inclusive)."""
    cmd = f"git log {start_ref}^..{end_ref} --no-merges --pretty=format:'%H' -- {file_path}"
    commits = run_command(cmd)
    return commits.split("\n") if commits else []


def get_commit_details(commit_hash):
    """Get the details of a specific commit."""
    # Get commit message
    message = run_command(f"git show -s --format=%B {commit_hash}")

    # Get modified files
    files = run_command(f"git show --name-only --format='' {commit_hash}")
    modified_files = [f for f in files.split("\n") if f]

    # Get author name and email
    author = run_command(f"git show -s --format='%an <%ae>' {commit_hash}")

    # Get commit date
    date = run_command(f"git show -s --format='%ci' {commit_hash}")

    return {
        "hash": commit_hash,
        "author": author,
        "date": date,
        "message": message,
        "modified_files": modified_files,
    }


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Analyze commits that modified kernel/bpf/verifier.c between two git references."
    )
    parser.add_argument(
        "start_ref", help="Starting git reference (tag, branch, or commit hash)"
    )
    parser.add_argument(
        "end_ref", help="Ending git reference (tag, branch, or commit hash)"
    )

    args = parser.parse_args()

    # Path to the file we're interested in
    target_file = "kernel/bpf/verifier.c"

    # Check if we're in a git repository
    if not os.path.exists(".git"):
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)

    # Verify that the refs exist
    try:
        run_command(f"git rev-parse {args.start_ref}")
        run_command(f"git rev-parse {args.end_ref}")
    except subprocess.CalledProcessError:
        print(f"Error: One or both git references do not exist", file=sys.stderr)
        sys.exit(1)

    print(
        f"Analyzing commits between {args.start_ref} and {args.end_ref} (inclusive) that modified {target_file}",
        file=sys.stderr,
    )

    # Prepare data structure for results
    results = {
        "metadata": {
            "target_file": target_file,
            "start_ref": args.start_ref,
            "end_ref": args.end_ref,
        },
        "commits": [],
    }

    # Get all commits that touched the target file between the refs
    commits = get_commits_between_refs(args.start_ref, args.end_ref, target_file)

    # Get details for each commit
    for commit_hash in commits:
        if commit_hash:  # Skip empty lines
            commit_details = get_commit_details(commit_hash)
            results["commits"].append(commit_details)

    results["metadata"]["commit_count"] = len(results["commits"])

    # Output the results as JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
