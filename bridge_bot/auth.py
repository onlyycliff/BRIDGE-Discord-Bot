from flask_login import UserMixin


class CoachUser(UserMixin):
    """Thin adapter — adds Flask-Login behavior to a Coach model instance.

    The model layer stays pure (no Flask dependency). This adapter lives
    in the web layer where it belongs.
    """
    def __init__(self, coach):
        self.id = coach.id
        self.email = coach.email
        self.name = coach.name
        self.password_hash = coach.password_hash
        self.created_at = coach.created_at
