from dataclasses import dataclass
# Colour, and other properties need to be specifiable at the plot x data level

# Properties inherit:
#  Default Individual -> Individual -> Default Trend -> Trend -> Plot Group -> Plot -> Subplot -> Line


@dataclass
class Appearance:
    """ Description of the appearance settings of some data in a plot

    Dicts/namedtuples have much of this stuff implemented
    but dicts are not good

    ...named tuple would probably be fine
    """
    colour: str | None = None
    trend_scheme: str | None = None

    def override(self, other: "Appearance"):
        colour = self.colour if other.colour is None else other.colour
        trend_scheme = self.trend_scheme if other.trend_scheme is None else other.trend_scheme
        return Appearance(
            colour=colour,
            trend_scheme=trend_scheme)


class AppearanceContainer:
    """ Base class for a node in the appearance heirachy"""
    def __init__(self, appearance_parent: "AppearanceContainer"):
        self.appearance_parent = appearance_parent
        self.children = []

        self.appearance = Appearance()

    def appearance(self):
        return self.appearance_parent.appearance.override(self.appearance)

    def add(self, child: "AppearanceContainer"):
        self.children.append(child)
        child.parent = self


class Default(AppearanceContainer):
    """ Root node """
    def appearance(self):
        return Appearance(
            colour='k',
            trend_scheme='jet')

