#!/bin/bash

# Disable the pager for all git commands
export GIT_PAGER=cat

# Process each merge commit in bpf-next master
git log --merges v6.3^..v6.13 --format="%H" | while read merge_hash; do
    # Get merge subject
    merge_subject=$(git show -s --format="%s" $merge_hash)
    
    # Get the first parent (target branch) and second parent (source branch)
    parent1=$(git rev-parse $merge_hash^1)
    parent2=$(git rev-parse $merge_hash^2)
    
    # Check if this merge includes any other merges
    if git log --merges --oneline $parent1..$parent2 | grep -q .; then
        continue
    fi

    # Hacky check to avoid higher level pulls (usually tags)
    if echo "$merge_subject" | grep -q "Merge tag"; then
        continue
    fi
    
    # Check if this merge affects verifier code
    if git log --oneline $parent1..$parent2 -- kernel/bpf/verifier.c | grep -q .; then
        echo "================================================================="
        echo "MERGE: $merge_subject"
        echo "HASH: $merge_hash"
        echo ""
        
        # Show merge commit message as potential cover letter
        echo "COVER LETTER / MERGE MESSAGE:"
        git show -s --format="%b" $merge_hash
        echo ""
        
        # List all patches in this merge that touch BPF code
        echo "PATCHES:"
        git log --reverse --format="  %h %s" $parent1..$parent2
        echo ""
    fi
done
