from typing import TypeVar

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHBoxLayout, \
    QGridLayout, QPushButton, QAbstractItemView

import numpy as np
from dataclasses import dataclass


import matplotlib

matplotlib.use('QtAgg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from random_names import random_name

T = TypeVar("T")
def flatten(data: list[list[T]]) -> list[T]:
    """ Why is this not a builtin"""
    return [xx for x in data for xx in x]

@dataclass
class PlotInstruction:
    plot_keywords: dict
    x: np.ndarray
    y: np.ndarray


class Modifier(QTreeWidgetItem):
    def __init__(self, info: str):
        super().__init__(["Modifier: "+info])

    def apply_modifier(self, instruction: list[PlotInstruction]) -> list[PlotInstruction]:
        raise NotImplementedError("apply_modifier not implemented in base class")

class TrendModifier(Modifier):
    def __init__(self, color_scheme: str):
        self.color_scheme = color_scheme
        super().__init__(f"scheme={color_scheme}")

    def apply_modifier(self, instructions: list[PlotInstruction]) -> list[PlotInstruction]:
        out = []
        cmap = matplotlib.colormaps[self.color_scheme]
        n = len(instructions)

        for index, instruction in enumerate(instructions):
            new_dict = instruction.plot_keywords.copy()
            new_dict["color"] = cmap(index/(n-1))
            out.append(PlotInstruction(new_dict, instruction.x, instruction.y))

        return out

class DataModifier(Modifier):
    def __init__(self, color: str | None = None, linestyle: str | None=None):
        self.color = color
        self.linestyle = linestyle

        parts = [None if color is None else f"color={color}",
                 None if linestyle is None else f"linestyle={linestyle}"]

        super().__init__(", ".join([part for part in parts if part is not None]))

    def apply_modifier(self, instructions: list[PlotInstruction]) -> list[PlotInstruction]:
        out = []
        for instruction in instructions:
            new_dict = instruction.plot_keywords.copy()

            if self.color is not None:
                new_dict["color"] = self.color

            if self.linestyle is not None:
                new_dict["linestyle"] = self.linestyle

            out.append(PlotInstruction(new_dict, instruction.x, instruction.y))
        return out


class Plottable(QTreeWidgetItem):
    def plot_instructions(self) -> list[PlotInstruction]:
        out = self.referenced_plot_instructions()
        for modifier in self.modifiers():
            out = modifier.apply_modifier(out)
        return out

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        raise NotImplementedError(f"Cannot get referenced plot instructions in {self.__class__.__name__}")

    def modifiers(self) -> list[Modifier]:
        return [self.child(child_index)
                for child_index in range(self.childCount())
                if isinstance(self.child(child_index), Modifier)]


class DataRoot(QTreeWidgetItem):
    def __init__(self):
        super().__init__(["Data"])


class TrendsRoot(QTreeWidgetItem):
    def __init__(self):
        super().__init__(["Trends"])


class DataItem(Plottable):
    def __init__(self):
        self.name = random_name()
        super().__init__(["Data: "+self.name])

        self.x = np.linspace(0,10,100)
        self.y = np.sin(0.3*(1+np.random.random())*self.x + 2*np.pi*np.random.random())

    def create_link(self):
        return DataLink(self)

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        return [PlotInstruction({}, self.x, self.y)]

class DataLink(Plottable):
    def __init__(self, src: DataItem):
        self.src = src
        super().__init__(["Data Link: "+self.src.name])

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        return self.src.plot_instructions()


class TrendItem(Plottable):
    def __init__(self):
        self.name = random_name()
        super().__init__(["Trend: "+self.name])

    def create_link(self):
        return TrendLink(self)

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        return flatten([self.child(child_index).plot_instructions()
                for child_index in range(self.childCount())
                if isinstance(self.child(child_index), DataLink)])


class TrendLink(Plottable):
    def __init__(self, src: TrendItem):
        self.src = src
        super().__init__(["Trend Link: "+self.src.name])

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        return self.src.plot_instructions()


class PlotRoot(QTreeWidgetItem):
    def __init__(self):
        super().__init__(["Plots"])


class Plot(Plottable):
    def __init__(self):
        self.name = random_name()
        super().__init__(["Plot: "+self.name])

        self.figure = Figure(figsize=(5, 3))
        self.figure_canvas = FigureCanvas(self.figure)
        self.figure.gca().set_title(self.name)

    def referenced_plot_instructions(self) -> list[PlotInstruction]:
        children = [self.child(child_index) for child_index in range(self.childCount())]
        return flatten([child.plot_instructions()
                for child in children
                if isinstance(child, Plottable)])

    def updatePlot(self):

        self.figure.clf()
        axes = self.figure.gca()
        axes.set_title(self.name)

        axes.set_xlabel("X")
        axes.set_ylabel("Y")

        for plot_instruction in self.plot_instructions():
            axes.plot(plot_instruction.x, plot_instruction.y, **plot_instruction.plot_keywords)

        self.figure.tight_layout()
        self.figure.canvas.draw()


class DropSensitiveTree(QTreeWidget):

    itemDropped = Signal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.itemDropped.emit()

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.main_layout = QHBoxLayout()
        self.tree = DropSensitiveTree()
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)

        self.plot_widget = QWidget()
        self.plot_layout = QGridLayout()
        self.plot_widget.setLayout(self.plot_layout)

        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_widget.setLayout(self.left_layout)

        self.left_layout.addWidget(self.tree)

        self.main_layout.addWidget(self.left_widget)
        self.main_layout.addWidget(self.plot_widget)

        # Build tree

        self.data_root = DataRoot()
        self.trend_root = TrendsRoot()
        self.plots_root = PlotRoot()

        # Plots


        self.plot1 = Plot()
        self.plot2 = Plot()
        self.plot3 = Plot()
        self.plot4 = Plot()

        self.plot_layout.addWidget(self.plot1.figure_canvas, 0, 0)
        self.plot_layout.addWidget(self.plot2.figure_canvas, 0, 1)
        self.plot_layout.addWidget(self.plot3.figure_canvas, 1, 0)
        self.plot_layout.addWidget(self.plot4.figure_canvas, 1, 1)

        self.plots_root.addChild(self.plot1)
        self.plots_root.addChild(self.plot2)
        self.plots_root.addChild(self.plot3)
        self.plots_root.addChild(self.plot4)

        # Data

        datas = [DataItem() for _ in range(10)]

        for data in datas:
            self.data_root.addChild(data)

        trends = [TrendItem(), TrendItem()]

        for i, trend in enumerate(trends):
            self.trend_root.addChild(trend)
            for k in range(i*5, (i+1)*5):
                trend.addChild(datas[k].create_link())

        self.plot1.addChild(datas[0].create_link())
        self.plot1.addChild(datas[1].create_link())
        self.plot2.addChild(datas[0].create_link())
        self.plot2.addChild(datas[1].create_link())
        self.plot2.addChild(datas[3].create_link())
        self.plot3.addChild(trends[0].create_link())
        self.plot4.addChild(trends[0].create_link())
        self.plot4.addChild(trends[1].create_link())


        # Put stuff in places

        self.tree.addTopLevelItem(self.data_root)
        self.tree.addTopLevelItem(self.trend_root)
        self.tree.addTopLevelItem(self.plots_root)

        self.tree.setHeaderHidden(True)

        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(1, 2)

        self.setLayout(self.main_layout)

        self.tree.itemDropped.connect(self.updatePlots)

        # Buttons

        self.button_panel = QWidget()
        self.button_layout = QGridLayout()
        self.button_panel.setLayout(self.button_layout)

        red = QPushButton("Red")
        green = QPushButton("Green")
        blue = QPushButton("Blue")

        solid = QPushButton("Solid")
        dash = QPushButton("Dash")
        dot = QPushButton("Dot")

        jet = QPushButton("Jet")
        spring = QPushButton("Spring")
        grey = QPushButton("Grey")

        red.clicked.connect(self.addDataModifier(color='r'))
        green.clicked.connect(self.addDataModifier(color='g'))
        blue.clicked.connect(self.addDataModifier(color='b'))

        solid.clicked.connect(self.addDataModifier(linestyle="solid"))
        dash.clicked.connect(self.addDataModifier(linestyle="dashed"))
        dot.clicked.connect(self.addDataModifier(linestyle="dotted"))

        jet.clicked.connect(self.addTrendModifier("jet"))
        spring.clicked.connect(self.addTrendModifier("spring"))
        grey.clicked.connect(self.addTrendModifier("gray"))

        self.button_layout.addWidget(red, 0, 0)
        self.button_layout.addWidget(green, 0, 1)
        self.button_layout.addWidget(blue, 0, 2)

        self.button_layout.addWidget(solid, 1, 0)
        self.button_layout.addWidget(dash, 1, 1)
        self.button_layout.addWidget(dot, 1, 2)

        self.button_layout.addWidget(jet, 2, 0)
        self.button_layout.addWidget(spring, 2, 1)
        self.button_layout.addWidget(grey, 2, 2)

        self.left_layout.addWidget(self.button_panel)



        self.updatePlots()



    def updatePlots(self):
        self.plot1.updatePlot()
        self.plot2.updatePlot()
        self.plot3.updatePlot()
        self.plot4.updatePlot()

    def addDataModifier(self, color: str | None=None, linestyle: str | None=None):
        def action():
            self.tree.addTopLevelItem(DataModifier(color, linestyle))
        return action

    def addTrendModifier(self, color_scheme: str):
        def action():
            self.tree.addTopLevelItem(TrendModifier(color_scheme))

        return action


if __name__ == "__main__":
    import sys

    app = QApplication([])

    window = TestWindow()
    window.show()

    sys.exit(app.exec())