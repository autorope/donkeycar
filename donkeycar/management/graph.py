from kivy.properties import ListProperty, ObjectProperty, StringProperty, \
    NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.graphics import Color, Line
from kivy.app import App

import numpy as np
import sys
from random import random
import pandas as pd
from kivy.uix.widget import Widget

Builder.load_string('''
#: import platform sys.platform
<LegendLabel>:
    orientation: 'horizontal'
    Label:
        size_hint_x: 0.25
        canvas.before:
            Color:
                hsv: root.hsv + [1]
            Line:
                width: 1.5
                points: [self.x, self.y + self.size[1]/2, self.x + self.size[0], self.y + self.size[1]/2]
    Label:
        text: root.text
        text_size: self.size
        font_size: sp(12)
        halign: 'center'
        valign: 'middle'

<PlotArea>:


<TsPlot>:
    orientation: 'vertical'
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            orientation: 'vertical'
            PlotArea: 
                id: plot
                size_hint_y: 8.0
                on_size: self.draw_axes()
            BoxLayout:
                id: x_ticks
                orientation: 'horizontal'
            Label:
                id: index_label
                size_hint_y: None
                halign: 'center'
                valign: 'top'
                font_size: 12 if platform == 'linux' else 24
                size: self.texture_size
                text: 'index'
        BoxLayout:
            id: legend
            size_hint_x: 0.15
            orientation: 'vertical' 
''')


class PlotArea(Widget):
    """ The graph area of the time series plot """
    offset = [50, 20]
    bounding_box = ListProperty()

    def make_bounding_box(self):
        return [[self.x + self.offset[0],
                 self.y + self.offset[1]],
                [self.x + self.size[0] - self.offset[0],
                 self.y + self.size[1] - self.offset[1]]]

    def draw_axes(self):
        self.canvas.clear()
        self.bounding_box = self.make_bounding_box()
        bb = self.bounding_box
        with self.canvas:
            Color(.9, .9, .9, 1.)
            points = [bb[0][0], bb[1][1], bb[0][0], bb[0][1], bb[1][0], bb[0][1]]
            Line(width=1 if sys.platform == 'linux' else 1.5, points=points)

    def draw_x_ticks(self, num_ticks):
        x_length = self.bounding_box[1][0] - self.bounding_box[0][0]
        for i in range(num_ticks + 1):
            i_len = x_length * i / num_ticks
            top = [self.bounding_box[0][0] + i_len, self.bounding_box[0][1]]
            bottom = [top[0], top[1] - self.offset[1] / 2]
            with self.canvas:
                Color(.9, .9, .9, 1.)
                Line(width=1 if sys.platform == 'linux' else 1.5, points=bottom+top)

    def get_x(self, num_points):
        x_scale = (self.bounding_box[1][0] - self.bounding_box[0][0]) \
                  / (num_points - 1)
        x_trafo = x_scale * np.array(range(num_points)) + self.bounding_box[0][0]
        return x_trafo

    def transform_y(self, y):
        y_scale = (self.bounding_box[1][1] - self.bounding_box[0][1]) \
                  / (y.max() - y.min())
        y_trafo = y_scale * (y - y.min()) + self.y + self.offset[1]
        return y_trafo

    def add_line(self, y_points, len, hsv):
        x_transformed = self.get_x(len)
        y_transformed = self.transform_y(y_points)
        xy_points = list()
        for x, y, in zip(x_transformed, y_transformed):
            if not xy_points or x > xy_points[-2] + 1:
                xy_points += [x, y]
        with self.canvas:
            Color(*hsv, mode='hsv')
            Line(points=xy_points, width=1 if sys.platform == 'linux' else 1.5)


class TsPlot(BoxLayout):
    """ Time series plot. Can be integrated as a widget into another kivy
        app."""
    len = 0
    x_ticks = 10
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def draw_axes(self):
        self.ids.x_ticks.clear_widgets()
        self.ids.legend.clear_widgets()
        self.len = 0
        self.ids.plot.draw_axes()

    def draw_x_ticks(self):
        if self.len == 0:
            return
        self.ids.plot.draw_x_ticks(self.x_ticks)
        for i in range(self.x_ticks + 1):
            tick_label = Label(text=str(int(i * self.len / self.x_ticks)),
                               font_size=12 if sys.platform == 'linux' else 24)
            self.ids.x_ticks.add_widget(tick_label)

    def add_line(self, y_points, idx):
        if self.len == 0:
            self.len = len(y_points)
            self.draw_x_ticks()
        hsv = idx / len(self.df.columns), 0.7, 0.8
        self.ids.plot.add_line(y_points, self.len, hsv)
        l = LegendLabel(text=self.df.columns[idx], hsv=hsv)
        self.ids.legend.add_widget(l)

    def on_df(self, e=None, z=None):
        self.draw_axes()
        if self.df is not None:
            self.ids.index_label.text = self.df.index.name or 'index'
        else:
            return
        self.len = 0
        for i, col in enumerate(self.df.columns):
            y = self.df[col]
            self.add_line(y, i)

    def set_df(self, e):
        n = int(random() * 20) + 1
        cols = ['very very long line ' + str(i) for i in range(n)]
        df = pd.DataFrame(np.random.randn(20, n), columns=cols)
        df.index.name = 'My Index'
        self.df = df


class LegendLabel(BoxLayout):
    hsv = ListProperty()
    text = StringProperty()
    pass


class GraphApp(App):
    """ Test app for time series graph. """
    def build(self):
        b = BoxLayout(orientation='vertical')
        ts_plot = TsPlot()
        b.add_widget(ts_plot)
        btn = Button(text='Create random series', size_hint_y=0.1)
        btn.bind(on_press=ts_plot.set_df)
        b.add_widget(btn)
        return b


if __name__ == '__main__':
    GraphApp().run()
