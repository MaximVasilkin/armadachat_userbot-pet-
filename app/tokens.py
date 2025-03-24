import datetime


class Token:
    def __init__(self,
                 value: str,
                 requests_limit: int = 200,
                 renew_period: datetime.timedelta = datetime.timedelta(days=1)):

        self.value = value
        self.requests_limit = requests_limit
        self.requests_remaining = requests_limit
        self.renew_date = None
        self.renew_period = renew_period

    def is_actual(self) -> bool:
        return bool(self.requests_remaining)

    def is_ready_to_renew(self) -> bool:
        return bool(self.renew_date and (datetime.datetime.now() > self.renew_date))

    def renew(self):
        self.requests_remaining = self.requests_limit
        self.renew_date = None

    def get(self):
        if not self.is_actual() and self.is_ready_to_renew():
            self.renew()

        if self.is_actual():
            self.requests_remaining -= 1
            if not self.requests_remaining:
                self.renew_date = datetime.datetime.now() + self.renew_period
            return self.value


def get_token(tokens: list[Token, ...]) -> str:
    for token in tokens:
        token_value = token.get()
        if token_value:
            return token_value
    raise ValueError('No token at the moment')

