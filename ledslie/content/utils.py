# Ledslie, a community information display
# Copyright (C) 2017-18  Chotee@openended.eu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from typing import Any


class CircularBuffer(object):
    """
    I am a buffer with entries that you can always call next() for a new entry. Once the entries are exhausted, the
    first will returned again.
    """
    def __init__(self, elements=None):
        self._elems = []
        self._table = {}
        self._curr = -1
        self._id_counter = -1
        if elements:
            for element in reversed(elements):
                self.add(element)

    def add(self, element: Any) -> int:
        """
        I add an element to the buffer. I also make sure that the next call of next() will return the last element
        added.
        :param element: The object to add to the buffer
        :type element: Any
        :return: An id of the object just added.
        """
        self._id_counter += 1
        e_obj = [element]  # Create a list object, so that we can update just the content of the first element.
        self._table[self._id_counter] = e_obj
        self._elems.insert(self._curr+1, e_obj)
        return self._id_counter

    def remove(self, value: Any):
        """
        Remove value from the buffer.

        :param value: The value to remove
        :type value: object
        """
        # Remove from the list
        i = self._elems.index([value])
        if self._curr >= i:
            self._curr -= 1
        self._elems.pop(i)
        found = None

        # Remove from the Table
        for k, v in list(self._table.items()):
            if v == value:
                found = k
                break
        if found:
            del self._table[k]

    def remove_by_id(self, id: int):
        """
        Remove the content by the contents id.

        :param id: The id of the object to remove.
        :type id: int
        """
        self.remove(self._table[id][0])

    def update(self, elem_id: int, new_value: Any):
        self._table[elem_id][0] = new_value

    def __contains__(self, elem_id) -> bool:
        """
        I return True if the elem_id is in the buffer.
        :param elem_id: The id of the element
        :return: True if found.
        :rtype: bool
        """
        return elem_id in self._table

    def __next__(self):
        """
        I return a single entry in the buffer.
        :return: An entry in the buffer.
        :rtype: object
        """
        self._curr += 1
        try:
            return self._elems[self._curr][0]
        except IndexError:
            self._curr = 0
            return self._elems[self._curr][0]

    @property
    def pos(self) -> int:
        """
        Returns the current position in the circular buffer
        :return: The position
        :rtype: int
        """
        return self._curr

    def __iter__(self):
        return self

    def __len__(self):
        return len(self._elems)
