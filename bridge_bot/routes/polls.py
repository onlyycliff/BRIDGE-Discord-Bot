"""Poll routes — wiring module.

Registers handler modules onto a single ``polls_bp`` blueprint
so endpoint names stay stable (``api.polls.*``).
"""

from flask import Blueprint

from bridge_bot.routes.poll_create import register_create_end
from bridge_bot.routes.poll_read import register_read
from bridge_bot.routes.poll_votes import register_votes
from bridge_bot.routes.poll_analytics import register_analytics

polls_bp = Blueprint('polls', __name__)

register_create_end(polls_bp)
register_read(polls_bp)
register_votes(polls_bp)
register_analytics(polls_bp)
