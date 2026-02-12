#!/usr/bin/env bash
set -euo pipefail

pr_number="${1:-}"
repo_full_name="${2:-}"

if [[ -z "$pr_number" ]]; then
  pr_number="$(gh pr view --json number -q .number)"
fi

if [[ -z "$repo_full_name" ]]; then
  repo_full_name="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

owner="${repo_full_name%/*}"
repo="${repo_full_name#*/}"

query='query($owner:String!, $name:String!, $number:Int!) { repository(owner:$owner, name:$name) { pullRequest(number:$number) { reviewThreads(first:100) { nodes { id isResolved comments(last:100) { nodes { id body url createdAt author { login } } } } } } } }'

raw_json="$(gh api graphql -F owner="$owner" -F name="$repo" -F number="$pr_number" -f query="$query")"
review_comments_json="$(
  gh api --paginate "repos/$owner/$repo/pulls/$pr_number/comments?per_page=100" \
    | jq -s 'add'
)"

jq -n \
  --arg repository "$repo_full_name" \
  --argjson pullRequest "$pr_number" \
  --argjson threadData "$raw_json" \
  --argjson reviewComments "$review_comments_json" '
  (
    [
      $threadData.data.repository.pullRequest.reviewThreads.nodes[]
      | select(.isResolved == false)
      | .comments.nodes[]
      | .url
    ]
    | unique
  ) as $openCommentUrls
  | ($reviewComments
    | map(select(.html_url as $u | $openCommentUrls | index($u)))
    | map({
        key: .html_url,
        value: {
          path: (.path // null),
          line: (.line // null),
          startLine: (.start_line // null),
          side: (.side // null),
          startSide: (.start_side // null),
          diffHunk: (.diff_hunk // null),
          commitId: (.commit_id // null),
          originalCommitId: (.original_commit_id // null)
        }
      })
    | from_entries) as $codeLocationByUrl
  | (
      [
        $threadData.data.repository.pullRequest.reviewThreads.nodes[]
        | select(.isResolved == false)
        | .comments.nodes[]
      ] | length
    ) as $openReviewCommentCount
  | {
      repository: $repository,
      pullRequest: $pullRequest,
      unresolvedThreadCount: (
        [$threadData.data.repository.pullRequest.reviewThreads.nodes[]
          | select(.isResolved == false)] | length
      ),
      totalReviewCommentCount: $openReviewCommentCount,
      unresolvedThreads: [
        $threadData.data.repository.pullRequest.reviewThreads.nodes[]
        | select(.isResolved == false)
        | {
            threadId: .id,
            commentCount: (.comments.nodes | length),
            reviewer: ((.comments.nodes[-1].author.login) // "unknown"),
            commentUrl: ((.comments.nodes[-1].url) // ""),
            commentBody: ((.comments.nodes[-1].body) // ""),
            codeLocation: ($codeLocationByUrl[(.comments.nodes[-1].url)] // null),
            comments: [
              .comments.nodes[]
              | {
                  reviewer: (.author.login // "unknown"),
                  commentUrl: (.url // ""),
                  commentBody: (.body // ""),
                  createdAt: (.createdAt // null),
                  codeLocation: ($codeLocationByUrl[.url] // null)
                }
            ]
          }
      ]
    }'
