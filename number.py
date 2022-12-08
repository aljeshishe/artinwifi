import copy
from typing import Iterable, Generator, Union

DataT = list[int]


def enum(data: DataT) -> Generator[int, None, None]:
    yield from range(0, len(data))
    # for i in
    #     yield i


def _equlize_len(left: DataT, right:DataT):
    left_len = len(left)
    right_len = len(right)
    postfix = [0] * abs(left_len - right_len)
    if left_len > right_len:
        right += postfix
        return

    if left_len < right_len:
        left += postfix
        return


class Number:
    def __init__(self, data: DataT, base: int) -> None:
        self.data: DataT = data
        self.base: int = base

    @staticmethod
    def from_str(value: str, alphabet: str) -> "Number":
        return Number(data=[alphabet.find(c) for c in value][::-1], base=len(alphabet))

    @staticmethod
    def from_base_10(value: int, base: int) -> "Number":
        data = []
        while value != 0:
            value, remainder = divmod(value, base)
            data.append(remainder)
        return Number(data=data, base=base)

    def to_base_10(self) -> int:
        result = sum(pow(self.base, i) * value for i, value in enumerate(self.data))
        return result

    def to_str(self, alphabet: str) -> str:
        return "".join(alphabet[idx] for idx in self.data)[::-1]

    def __str__(self):
        return f"Number(base={self.base}, data={self.data})"

    __repr__ = __str__

    def __eq__(self, other: "Number"):
        return self.base == other.base and self.data == other.data

    def __add__(self, right: Union[int, "Number"]) -> "Number":
        if isinstance(right, int):
            right = Number.from_base_10(right, base=self.base)

        left = copy.deepcopy(self)
        _equlize_len(left.data, right.data)
        for li, ri in zip(enum(left.data), enum(right.data)):
            left.data[li] += right.data[ri]
        left._on_overflow()
        return left

    def __sub__(self, right: Union[int, "Number"]):
        if isinstance(right, int):
            right = Number.from_base_10(right, base=self.base)

        left = copy.deepcopy(self)
        _equlize_len(self.data, right.data)
        for li, ri in zip(enum(left.data), enum(right.data)):
            left.data[li] -= right.data[ri]
        left._on_overflow()
        return left

    def _on_overflow(self):
        for i in enum(self.data):
            if self.data[i] >= self.base:
                self.data[i] = 0
                if i + 1 >= len(self.data):
                    self.data.append(0)
                self.data[i + 1] += 1

            if self.data[i] < 0:
                self.data[i] += self.base
                if i + 1 >= len(self.data):
                    self.data.append(0)
                self.data[i + 1] -= 1

