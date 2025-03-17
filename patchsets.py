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


def get_merge_commits(start_ref, end_ref):
    """Get all merge commits between two git references."""
    cmd = f"git log --merges {start_ref}^..{end_ref} --format='%H'"
    merges = run_command(cmd)
    return merges.split("\n") if merges else []


def get_merge_details(merge_hash):
    """Get details about a merge commit."""
    # Get merge subject
    subject = run_command(f"git show -s --format='%s' {merge_hash}")
    
    # Get merge message body
    body = run_command(f"git show -s --format='%b' {merge_hash}")
    
    # Get first and second parents
    parent1 = run_command(f"git rev-parse {merge_hash}^1")
    parent2 = run_command(f"git rev-parse {merge_hash}^2")
    
    # Get author name and email
    author = run_command(f"git show -s --format='%an <%ae>' {merge_hash}")
    
    # Get commit date
    date = run_command(f"git show -s --format='%ci' {merge_hash}")
    
    return {
        "hash": merge_hash,
        "subject": subject,
        "body": body,
        "author": author,
        "date": date,
        "parent1": parent1,
        "parent2": parent2,
    }


def get_commits_in_merge(parent1, parent2):
    """Get all non-merge commits between two parent commits."""
    cmd = f"git log --reverse --no-merges --format='%H' {parent1}..{parent2}"
    commits = run_command(cmd)
    return commits.split("\n") if commits else []


def get_commit_details(commit_hash):
    """Get the details of a specific commit."""
    # Get commit subject
    subject = run_command(f"git show -s --format='%s' {commit_hash}")
    
    # Get commit message
    message = run_command(f"git show -s --format='%b' {commit_hash}")
    
    # Get modified files
    files = run_command(f"git show --name-only --format='' {commit_hash}")
    modified_files = [f for f in files.split("\n") if f]
    
    # Get author name and email
    author = run_command(f"git show -s --format='%an <%ae>' {commit_hash}")
    
    # Get commit date
    date = run_command(f"git show -s --format='%ci' {commit_hash}")
    
    return {
        "hash": commit_hash,
        "subject": subject,
        "message": message,
        "author": author,
        "date": date,
        "modified_files": modified_files,
    }


def check_merge_affects_verifier(parent1, parent2, target_file):
    """Check if merge affects the target file."""
    cmd = f"git log --oneline {parent1}..{parent2} -- {target_file}"
    result = run_command(cmd)
    return bool(result)


def check_merge_contains_merges(parent1, parent2):
    """Check if this merge includes any other merges."""
    cmd = f"git log --merges --oneline {parent1}..{parent2}"
    result = run_command(cmd)
    return bool(result)


def main():
    # Path to the file we're interested in
    target_file = "kernel/bpf/verifier.c"
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description=f"Find patchsets that modified {target_file} between two git references."
    )
    parser.add_argument(
        "start_ref", help="Starting git reference (tag, branch, or commit hash)"
    )
    parser.add_argument(
        "end_ref", help="Ending git reference (tag, branch, or commit hash)"
    )

    args = parser.parse_args()

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
        f"Analyzing merge commits between {args.start_ref} and {args.end_ref} that affect {target_file}",
        file=sys.stderr,
    )

    # Prepare data structure for results
    results = {
        "metadata": {
            "target_file": target_file,
            "start_ref": args.start_ref,
            "end_ref": args.end_ref,
        },
        "patchsets": [],
    }

    # Get all merge commits between the refs
    merge_commits = get_merge_commits(args.start_ref, args.end_ref)

    # Process each merge commit
    for merge_hash in merge_commits:
        if not merge_hash:  # Skip empty lines
            continue
            
        merge_details = get_merge_details(merge_hash)
        parent1 = merge_details["parent1"]
        parent2 = merge_details["parent2"]
        
        # Skip if this merge contains other merges
        if check_merge_contains_merges(parent1, parent2):
            continue
            
        # Skip if this is a tag merge
        if "Merge tag" in merge_details["subject"]:
            continue
            
        # Check if this merge affects verifier code
        if check_merge_affects_verifier(parent1, parent2, target_file):
            print(
                f"Found ({merge_hash})  {merge_details['subject']}",
                file=sys.stderr,
            )

            # Get all commits in this merge
            commit_hashes = get_commits_in_merge(parent1, parent2)
            commits = []
            
            for commit_hash in commit_hashes:
                if commit_hash:  # Skip empty lines
                    commit_details = get_commit_details(commit_hash)
                    commits.append(commit_details)
            
            # Create patchset entry
            patchset = {
                "merge_hash": merge_hash,
                "merge_subject": merge_details["subject"],
                "merge_body": merge_details["body"],
                "merge_author": merge_details["author"],
                "merge_date": merge_details["date"],
                "commits": commits,
            }
            
            results["patchsets"].append(patchset)

    results["metadata"]["patchset_count"] = len(results["patchsets"])

    # Output the results as JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
