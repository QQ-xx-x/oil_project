# -*- coding: utf-8 -*-
"""Central multi-document workspace used after project open."""

from PyQt5.QtWidgets import QTabWidget

from .viewport_placeholders import ChartViewport, ThreeDViewport, TwoDViewport, ViewPage


class WorkspaceTabs(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workspaceTabs")
        self.setTabsClosable(True)
        self.setMovable(True)

        self.two_d_primary = ViewPage(TwoDViewport())
        self.three_d = ViewPage(ThreeDViewport())
        self.chart = ViewPage(ChartViewport())
        self.two_d_secondary = ViewPage(TwoDViewport())

        self.addTab(self.two_d_primary, "2D窗口 7 [任意]")
        self.addTab(self.three_d, "3D窗口 5 [任意]")
        self.addTab(self.chart, "图表窗口 1")
        self.addTab(self.two_d_secondary, "2D窗口 4 [任意]")
        self.setCurrentIndex(1)

    def update_context(self, title, detail, preferred_view="3d", display_key=None):
        for page in [
                self.two_d_primary, self.three_d, self.chart,
                self.two_d_secondary]:
            page.set_context(title, detail, display_key)
        if preferred_view == "chart":
            self.setCurrentWidget(self.chart)
        elif preferred_view == "2d":
            self.setCurrentWidget(self.two_d_primary)
        else:
            self.setCurrentWidget(self.three_d)

    def set_layer_state(self, layer_key, enabled):
        self.three_d.set_layer_state(layer_key, enabled)

    def set_chart_data(self, chart_key, data):
        self.chart.set_chart_data(chart_key, data)
