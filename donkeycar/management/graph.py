from kivy.properties import ListProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.graphics import Color, Line
from kivy.app import App

import numpy as np
from random import random
import pandas as pd

Builder.load_string('''
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
        font_size: 24
        halign: 'center'
        valign: 'middle'

<TsPlot>:
    bounding_box: [[plot.x + self.offset[0], plot.y + self.offset[1]], [plot.x + plot.size[0] - self.offset[0], plot.y + plot.size[1] - self.offset[1]]]
    orientation: 'vertical'
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            orientation: 'vertical'
            Widget: 
                id: plot
                size_hint_y: 8.0
                on_size: root.draw_axes()
            BoxLayout:
                id: x_ticks
                orientation: 'horizontal'
            Label:
                id: index_label
                size_hint_y: None
                halign: 'center'
                valign: 'top'
                font_size: 24
                size: self.texture_size
                text: 'index'
        BoxLayout:
            id: legend
            size_hint_x: 0.15
            orientation: 'vertical' 
''')


class TsPlot(BoxLayout):
    offset = [50, 20]
    len = 0
    x_ticks = 10
    bounding_box = ListProperty()
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def draw_axes(self):
        plot = self.ids.plot
        plot.canvas.clear()
        self.ids.x_ticks.clear_widgets()
        self.ids.legend.clear_widgets()
        self.len = 0
        bb = self.bounding_box
        with self.ids.plot.canvas:
            Color(.9, .9, .9, 1.)
            points = [bb[0][0], bb[1][1], bb[0][0], bb[0][1], bb[1][0], bb[0][1]]
            Line(width=1.5, points=points)

    def draw_x_ticks(self):
        if self.len == 0:
            return
        plot = self.ids.plot
        x_length = plot.size[0] - 2 * self.offset[0]
        for i in range(self.x_ticks + 1):
            i_len = x_length * i / self.x_ticks
            top = [self.bounding_box[0][0] + i_len, self.bounding_box[0][1]]
            bottom = [top[0], top[1] - self.offset[1] / 2]
            with plot.canvas:
                Color(.9, .9, .9, 1.)
                Line(width=1.5, points=bottom+top)
            tick_label = Label(text=str(int(i * self.len / self.x_ticks)),
                               font_size=24)
            self.ids.x_ticks.add_widget(tick_label)

    def get_x(self, length):
        x_scale = (self.bounding_box[1][0] - self.bounding_box[0][0]) \
                  / (length - 1)
        x_trafo = x_scale * np.array(range(length)) + self.bounding_box[0][0]
        return x_trafo

    def transform_y(self, y):
        y_scale = (self.ids.plot.size[1] - 2 * self.offset[1]) \
                  / (y.max() - y.min())
        y_trafo = y_scale * (y - y.min()) + self.ids.plot.y + self.offset[1]
        return y_trafo

    def add_line(self, y_points, idx):
        if self.len == 0:
            self.len = len(y_points)
            self.draw_x_ticks()
        x_transformed = self.get_x(self.len)
        y_transformed = self.transform_y(y_points)
        xy_points = list()
        for x, y, in zip(x_transformed, y_transformed):
            xy_points += [x, y]
        hsv = idx / len(self.df.columns), 0.7, 0.8
        with self.ids.plot.canvas:
            Color(*hsv, mode='hsv')
            Line(points=xy_points, width=1.5)
        l = LegendLabel(text=self.df.columns[idx], hsv=hsv)
        self.ids.legend.add_widget(l)

    def on_df(self, e, z):
        self.ids.plot.canvas.clear()
        self.draw_axes()
        if self.df is not None:
            self.ids.index_label.text = self.df.index.name or 'index'
        else:
            return
        self.len = 0
        for i, col in enumerate(self.df.columns):
            y = self.df[col]
            self.add_line(y, i)

    def set_df(self):
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
    def build(self):
        return TsPlot()


if __name__ == '__main__':
    GraphApp().run()
