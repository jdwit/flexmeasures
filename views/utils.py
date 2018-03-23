"""Utilities for views"""
import os
import subprocess
from typing import List, Tuple
from datetime import datetime, timedelta

from flask import render_template, request, session, current_app
from bokeh.resources import CDN
from humanize import naturaldate, naturaltime

import models
from utils import time_utils


def render_bvp_template(html_filename: str, **variables):
    """Render template and add all expected template variables, plus the ones given as **variables."""
    if os.path.exists("static/documentation/html/index.html"):
        variables["documentation_exists"] = True
    else:
        variables["documentation_exists"] = False
    if "start_time" in session:
        variables["start_time"] = session["start_time"]
    else:
        variables["start_time"] = time_utils.get_default_start_time()
    if "end_time" in session:
        variables["end_time"] = session["end_time"]
    else:
        variables["end_time"] = time_utils.get_default_end_time()
    variables["page"] = html_filename.replace(".html", "")
    if "show_datepicker" not in variables:
        variables["show_datepicker"] = variables["page"] in ("analytics", "portfolio")
    variables["contains_plots"] = False
    if any([n.endswith("plots_div") for n in variables.keys()]):
        variables["contains_plots"] = True
        variables["bokeh_css_resources"] = CDN.render_css()
        variables["bokeh_js_resources"] = CDN.render_js()
    variables["resolution"] = session.get("resolution", "")
    variables["resolution_human"] = time_utils.freq_label_to_human_readable_label(session.get("resolution", ""))

    variables["git_version"], variables["git_commits_since"], variables["git_hash"] = get_git_description()
    app_start_time = current_app.config.get("START_TIME")
    now = datetime.now()
    if app_start_time >= now - timedelta(hours=24):
        variables["app_running_since"] = naturaltime(app_start_time)
    else:
        variables["app_running_since"] = naturaldate(app_start_time)

    return render_template(html_filename, **variables)


def get_git_description() -> Tuple[str, int, str]:
    """ Return the latest git version (tag) as a string, the number of commits since then as an int and the
    current commit hash as string. """
    def _minimal_ext_cmd(cmd: list):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env).communicate()[0]

    sha = "Unknown"
    commits_since = 0
    sha = "Unknown"
    try:
        git_output = _minimal_ext_cmd(['git', 'describe', '--always', '--long'])
        components = git_output.strip().decode('ascii').split('-')
        sha = components.pop()
        commits_since = int(components.pop())
        version = "-".join(components)
    except OSError as ose:
        current_app.logger.warn("Problem when reading git describe: %s" % ose)
        pass

    return version, commits_since, sha


# TODO: replace these mock helpers when we have real auth & user groups

def check_prosumer_mock() -> bool:
    """Return whether we are showing the mocked version for a prosumer.
    Sets this in the session, as well."""
    if "prosumer_mock" in request.values:
        session["prosumer_mock"] = request.values.get("prosumer_mock")
    return session.get("prosumer_mock", "0") != "0"


def filter_mock_prosumer_assets(assets: List[models.Asset]) -> List[models.Asset]:
    """Return a list of assets based on the mock prosumer type in the session."""
    session_prosumer = session.get("prosumer_mock")
    if session_prosumer == "vehicles":
        return [a for a in assets if a.asset_type.name == "charging_station"]
    if session_prosumer == "buildings":
        return [a for a in assets if a.asset_type.name == "building"]
    if session_prosumer == "solar":
        return [a for a in assets if a.asset_type.name == "solar"]
    if session_prosumer == "onshore":
        return [a for a in assets if "onshore" in a.name]
    if session_prosumer == "offshore":
        return [a for a in assets if "offshore" in a.name]
    else:
        return assets
