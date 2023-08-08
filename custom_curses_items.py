from __future__ import annotations
import curses
from cursesmenu import CursesMenu, utils
from cursesmenu.items import FunctionItem, MenuItem, SubmenuItem, ExternalItem
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable

    from cursesmenu.curses_menu import CursesMenu

class CustomCursesMenu(CursesMenu):
    def _set_up_colors(self) -> None:
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_RED)
        self.highlight = curses.color_pair(3)

class CustomMenuItem(MenuItem):
    def __init__(
        self,
        text: str,
        menu: CustomCursesMenu | None = None,
        *,
        should_exit: bool = False,
        override_index: str | None = None,
        seperator: str |None = None
    ) -> None:
        self.text = text
        self.menu = menu
        self.should_exit = should_exit
        self.override_index = override_index
        self.seperator = seperator

    def show(self, index_text: str) -> str:
        if self.override_index is not None:
            index_text = self.override_index
        if self.seperator == None:
            self.seperator = ""
        return f"{index_text}{self.seperator}{self.text}"
    
    def set_up(self) -> None:
        """Perform setup for the item."""

    def action(self) -> None:
        """
        Do the main action for the item.

        If you're just writing a simple subclass, you shouldn't need set_up or clean_up.
        The menu just calls them in order. They are provided so you can make subclass
        hierarchies where the superclass handles some setup and cleanup for its
        subclasses.
        """

    def clean_up(self) -> None:
        """Perform cleanup for the item."""

    def get_return(self) -> Any:  # noqa: ANN401
        """
        Get the return value for this item.

        For a basic MenuItem, just forwards the return value from the menu.

        :return: The return value for the item.
        """
        if self.menu:
            return self.menu.returned_value
        return None

    def __str__(self) -> str:
        """Get a basic string representation of the item."""
        title = self.menu.title if self.menu else ""
        return f"{title} {self.text}"
    
class CustomExternalItem(CustomMenuItem):
    """A base class for menu items that need to exit the menu environment\
     temporarily."""

    def set_up(self) -> None:
        """Return the console to its original state and pause the menu."""
        assert self.menu is not None
        curses.def_prog_mode()
        self.menu.clear_screen()
        self.menu.pause()
        curses.endwin()
        utils.soft_clear_terminal()

    def clean_up(self) -> None:
        """Put the console back in curses mode and resume the menu."""
        assert self.menu is not None
        curses.reset_prog_mode()
        self.menu.resume()

class CustomFunctionItem(CustomExternalItem):
    """
    A menu item that executes a Python function with arguments.

    :param text: The text of the item
    :param function: A function or lambda to be executed when the item is selected
    :param args: A list of poitional arguments to be passed to the function
    :param kwargs: A dict of kwargs to be passed to the function
    :param menu: The menu that this item belongs to
    :param should_exit: Whether the menu will exit when this item is selected
    """

    def __init__(
        self,
        text: str,
        function: Callable[..., Any],
        args: list[Any] | None = None,
        kwargs: dict[Any, Any] | None = None,
        menu: CustomCursesMenu | None = None,
        *,
        should_exit: bool = False,
        override_index: str | None = None,
        seperator: str |None = None
    ) -> None:
        """Initialize the item."""
        super().__init__(
            text=text,
            menu=menu,
            should_exit=should_exit,
            override_index=override_index,
            seperator= seperator
        )
        self.function = function
        if args is None:
            args = []
        self.args: list[Any] = args
        if kwargs is None:
            kwargs = {}
        self.kwargs: dict[Any, Any] = kwargs

        self.return_value: Any = None

    def action(self) -> None:
        """Call the function with the provided arguments."""
        self.return_value = self.function(*self.args, **self.kwargs)

    def get_return(self) -> Any:  # noqa: ANN401
        """
        Get the returned value from the function.

        :return: The value returned from the function, or None if it hasn't been called.
        """
        return self.return_value

class CustomSubmenuItem(CustomMenuItem):
    """
    A menu item that opens a submenu.

    :param text: The text of the item
    :param submenu: A CursesMenu to be displayed when the item is selected
    :param menu: The menu that this item belongs to
    :param should_exit: Whether the menu will exit when this item is selected
    """

    def __init__(
        self,
        text: str,
        submenu: CustomCursesMenu | None = None,
        menu: CustomCursesMenu | None = None,
        *,
        should_exit: bool = False,
        override_index: str | None = None,
        seperator: str |None = None
    ) -> None:
        """Initialize the item."""
        self._submenu: CustomCursesMenu | None = submenu
        self._menu: CustomCursesMenu | None = menu
        if self._submenu:
            self._submenu.parent = menu
        super().__init__(
            text=text,
            menu=menu,
            should_exit=should_exit,
            override_index=override_index,
            seperator= seperator
        )

    @property
    def submenu(self) -> CustomCursesMenu | None:
        """Get the submenu associated with this item."""
        return self._submenu

    @submenu.setter
    def submenu(self, submenu: CustomCursesMenu | None) -> None:
        """Set the submenu and update its parent."""
        self._submenu = submenu
        if self._submenu is not None:
            self._submenu.parent = self._menu

    @property  # type: ignore[override]
    def menu(self) -> CustomCursesMenu | None:  # type: ignore[override]
        """Get the menu that this item belongs to."""
        return self._menu

    @menu.setter
    def menu(self, menu: CustomCursesMenu | None) -> None:
        """Set the menu for the item and update the submenu's parent."""
        self._menu = menu
        if self._submenu is not None:
            self._submenu.parent = menu

    def set_up(self) -> None:
        """Set the screen up for the submenu."""
        assert self.menu is not None
        self.menu.pause()
        self.menu.clear_screen()

    def action(self) -> None:
        """Start the submenu."""
        assert self.submenu is not None
        self.submenu.start()

    def clean_up(self) -> None:
        """Block until the submenu is done and then return to the parent."""
        assert self.menu is not None
        assert self.submenu is not None
        self.submenu.join()
        self.submenu.clear_screen()
        self.menu.resume()

    def get_return(self) -> Any:  # noqa: ANN401
        """Get the returned value from the submenu."""
        if self.submenu is not None:
            return self.submenu.returned_value
        return None