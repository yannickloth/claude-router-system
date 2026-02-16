#!/bin/bash
# Metrics Emission Helper Library
# Consolidates metrics writing logic shared across hooks
#
# Change Driver: METRICS_COLLECTION
# Purity: 1.0 (single change driver)
#
# Usage:
#   emit_metric "routing_recommendation" "$TIMESTAMP" "$PROJECT_ID" "$PROJECT_ROOT" \
#       --agent "$AGENT" --reason "$REASON" --confidence "$CONFIDENCE" --hash "$REQUEST_HASH"
#
# Replaces duplicated metrics logic in:
#   - user-prompt-submit.sh
#   - log-subagent-start.sh
#   - log-subagent-stop.sh

# Emit a metrics entry to the daily metrics file with atomic writes
# Arguments:
#   $1: record_type (e.g., "routing_recommendation", "agent_event")
#   $2: timestamp (ISO-8601 format)
#   $3: project_id
#   $4: project_root
#   ... remaining args: --key value pairs for additional fields
emit_metric() {
    local record_type="$1"
    local timestamp="$2"
    local project_id="$3"
    local project_root="$4"
    shift 4

    # Get metrics directory from caller's context
    # This should have been set by get_project_data_dir in the calling hook
    if [ -z "$METRICS_DIR" ]; then
        METRICS_DIR=$(get_project_data_dir "metrics")
    fi

    local today
    today=$(date +%Y-%m-%d)
    local metrics_file="$METRICS_DIR/${today}.jsonl"

    # Build jq arguments for additional fields dynamically
    local jq_args=()
    jq_args+=(--arg record_type "$record_type")
    jq_args+=(--arg timestamp "$timestamp")
    jq_args+=(--arg project_id "$project_id")
    jq_args+=(--arg project_root "$project_root")

    # Parse key-value pairs
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --*)
                local key="${1#--}"
                shift
                if [[ $# -gt 0 && "$1" != --* ]]; then
                    local value="$1"
                    shift

                    # Detect if value is JSON (starts with { or [) or numeric
                    if [[ "$value" =~ ^[\{\[].*$ ]] || [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ ! "$value" =~ ^[0-9]+[a-z] ]]; then
                        jq_args+=(--argjson "$key" "$value")
                    else
                        jq_args+=(--arg "$key" "$value")
                    fi
                else
                    shift || true
                fi
                ;;
            *)
                shift
                ;;
        esac
    done

    # Build base object
    local jq_expr='{record_type: $record_type, timestamp: $timestamp, project: {id: $project_id, root: $project_root}}'

    # Add dynamic fields
    for ((i=4; i<${#jq_args[@]}; i+=2)); do
        local key_arg="${jq_args[$i]}"
        local key_name="${key_arg#*\"}"
        key_name="${key_name%\"*}"
        jq_expr="$jq_expr | .${key_name} = \$${key_name}"
    done

    # Build and emit JSON
    local metrics_json
    metrics_json=$(jq -c -n "${jq_args[@]}" "$jq_expr")

    # Atomic append using flock
    (
        flock -x -w 5 200
        echo "$metrics_json" >> "$metrics_file"
    ) 200>"$metrics_file.lock"
}
