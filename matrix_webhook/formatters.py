"""Formatters for matrix webhook."""

import re


def grafana(data, headers):
    """Pretty-print a grafana notification."""
    text = ""
    if "title" in data:
        text = "#### " + data["title"] + "\n"
    if "message" in data:
        text = text + data["message"] + "\n\n"
    if "evalMatches" in data:
        for match in data["evalMatches"]:
            text = text + "* " + match["metric"] + ": " + str(match["value"]) + "\n"
    data["body"] = text
    return data

def grafana9(data, headers):
    """Pretty-print a grafana 9.x notification. (awsome!)"""
    text = ""
    ## fancy-emoji prefix (TODO: make configurable!)
    if data["state"] == "alerting":
        pre_icon="💔"
    #elif data["state"] == "resolved":
    #    pre_icon="💚"
    elif data["state"] == "nodata":
        pre_icon="❌"
    else:
        pre_icon="💚"

    # parsing/setting title
    if "title" in data:
        text = "####" + pre_icon + " " \
            + data["title"] + " " + pre_icon + "\n"
        m = re.search("\((.*?)\)", data["title"])
        if m:
            titl = m.group(0)
            if len(titl) > 2:
                text = "####" + pre_icon + " " + \
                titl[1:len(titl)-1:1] + \
                " " + pre_icon + "\n"

    # default message (body)
    if "message" in data:
        # something = json.loads(data["message"].decode())
        text = text + "```md\n" + data["message"] + "\n```" + "\n\n"

    #  pretty sure we should NOT use this
    #if "evalMatches" in data:
    #    for match in data["evalMatches"]:
    #        text = text + "* " + match["metric"] + ": " + str(match["value"]) + "\n"
    data["body"] = text
    return data

def github(data, headers):
    """Pretty-print a github notification."""
    # TODO: Write nice useful formatters. This is only an example.
    if headers["X-GitHub-Event"] == "push":
        pusher, ref, a, b, c = (
            data[k] for k in ["pusher", "ref", "after", "before", "compare"]
        )
        pusher = f"[@{pusher['name']}](https://github.com/{pusher['name']})"
        data["body"] = f"{pusher} pushed on {ref}: [{b} → {a}]({c}):\n\n"
        for commit in data["commits"]:
            data["body"] += f"- [{commit['message']}]({commit['url']})\n"
    else:
        data["body"] = "notification from github"
    data["digest"] = headers["X-Hub-Signature-256"].replace("sha256=", "")
    return data


def gitlab_gchat(data, headers):
    """Pretty-print a gitlab notification preformatted for Google Chat."""
    data["body"] = re.sub("<(.*?)\\|(.*?)>", "[\\2](\\1)", data["body"], re.MULTILINE)
    return data


def gitlab_teams(data, headers):
    """Pretty-print a gitlab notification preformatted for Microsoft Teams."""
    body = []
    for section in data["sections"]:
        if "text" in section.keys():
            text = section["text"].split("\n\n")
            text = ["* " + t for t in text]
            body.append("\n" + "  \n".join(text))
        elif all(
            k in section.keys()
            for k in ("activityTitle", "activitySubtitle", "activityText")
        ):
            text = section["activityTitle"] + " " + section["activitySubtitle"] + " → "
            text += section["activityText"]
            body.append(text)

    data["body"] = "  \n".join(body)
    return data
