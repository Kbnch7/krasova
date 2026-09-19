class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ShardUnavailableError(Exception):
    def __init__(self, shards):
        self.shards = sorted(shards)
        super().__init__(f"Шард недоступен: {', '.join(map(str, self.shards))}")
