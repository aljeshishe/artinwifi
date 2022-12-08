from number import Number


class Passwords:
    def __init__(self, start: str, end: str, alphabet: str):
        self.alphabet = alphabet
        self.start = Number.from_str(value=start, alphabet=self.alphabet)
        self.end = Number.from_str(value=end, alphabet=self.alphabet)
        self.total = (self.end - self.start).to_base_10() + 1

    def generator(self):
        current = self.start
        while True:
            yield current.to_str(alphabet=self.alphabet)

            if current == self.end:
                return

            current += 1
