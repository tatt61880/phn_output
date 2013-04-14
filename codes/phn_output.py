#!/usr/bin/env python
# vim: fileencoding=utf-8

"""
phn_output.py (Inkscape extension)
http://dl.dropbox.com/u/9975638/Algodoo/Inkscape/phn_output/index.html

Copyright (C) 2011-2012 Tatt61880 (タット) (tatt61880@gmail.com, @tatt61880)
Last Modified: 2012/05/04 09:56:46.
"""

#TODO Solve intersection of compound path
#TODO fill-rule:nonzero and self-intersection -> warning
#TODO use element support
#TODO Scene.Camera support
#TODO Texture support

__version__ = '0.0.6'

import sys
import re
from math import *
from random import random
import inspect # for __LINE__ info
from xml.etree.ElementTree import ElementTree, _ElementInterface

XMLNS = '{http://www.w3.org/2000/svg}'
SODIPODI = '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}'

# Accuracy for svg path to polygon.
ALLOWED_ANGLE = 1.0 * pi/180  # Unit: radians
# Accuracy for bezier curve to path. Points par bezier carve.
# NOTE: Larger value means better accrate
NODES_PER_BEZIER = 16  # Should be input as int type
# Accuracy for elliptical-arc: Central angle division frequency (radians)
# NOTE: Larger value means better accrate
ARC_NODES_FREQUENCY = 3.0 * pi/180

# Original data (SVG data) output
ORIGINAL_SVG_DATA_OUTPUT = True

# If MINIMUM_MODE == False, default params (eg. density = 2.0; etc.)
# NOTE: 'MINIMUM_MODE == False' is not tested at all.
MINIMUM_MODE = True

def warning(description): #{{{
    c = inspect.currentframe(1)
    if c is None:
        sys.stderr.write("\n## Warning\n")
        return
    line_no = c.f_lineno
    #filename = c.f_code.co_filename

    sys.stderr.write("\n## Warning - %s, line %s, in %s\n%s\n" % (
        __name__, str(line_no), c.f_code.co_name, description) )
#}}}

# ========================================
# Classes
# ========================================
class Matrix(tuple): #{{{
    def combine(self, other):
        if isinstance(other, self.__class__):
            return Matrix([
                self[0]*other[0] + self[2]*other[1],
                self[1]*other[0] + self[3]*other[1],
                self[0]*other[2] + self[2]*other[3],
                self[1]*other[2] + self[3]*other[3],
                self[0]*other[4] + self[2]*other[5] + self[4],
                self[1]*other[4] + self[3]*other[5] + self[5],
                ])
        else:
            raise ValueError('Argument should belongs to %s class' %
                             self.__class__.__name__)
    def __init__(self, data):
        if len(data) != 6:
            raise ValueError('%s must be 6 element array.' %
                             self.__class__.__name__)
#}}}
class Transforms(list):#{{{
    def _transform_to_matrix(self, transform):#{{{
        '''
        Comvert one transform into matrix
        transform: matrix | translate | scale | rotate | skewX | skewY
        '''
        label = transform[0]
        params = transform[1]

        if label == 'matrix':
            if len(params) == 6: matrix = params
        elif label == 'translate':
            if   len(params) == 1: matrix = (1, 0, 0, 1, params[0], 0)
            elif len(params) == 2: matrix = (1, 0, 0, 1, params[0], params[1])
        elif label == 'scale':
            if   len(params) == 1: matrix = (params[0], 0, 0, params[0], 0, 0)
            elif len(params) == 2: matrix = (params[0], 0, 0, params[1], 0, 0)
        elif label == 'rotate':
            if len(params) == 1:
                theta = params[0]*pi/180.
                matrix = (cos(theta), sin(theta), -sin(theta), cos(theta), 0, 0)
            elif len(params) == 3:
                # rotate(<rotate-angle> <cx> <cy>) equals following process:
                #  translate( <cx>,  <cy>) 
                #  rotate(<rotate-angle>)
                #  translate(-<cx>, -<cy>)
                transforms = Transforms([
                        ['translate', [ params[1],  params[2]]],
                        ['rotate', [params[0]]],
                        ['translate', [-params[1], -params[2]]]
                        ])
                matrix = transforms.to_matrix()
        elif label == 'skewX':
            if len(params) == 1:
                theta = params[0]*pi/180.
                matrix = (1, 0, tan(theta), 1, 0, 0)
        elif label == 'skewY':
            if len(params) == 1:
                theta = params[0]*pi/180.
                matrix = (1, tan(theta), 0, 1, 0, 0)
        else:
            warning("Unknown label for transform ('%s')." % label)
            matrix = (1,0,0,1,0,0)

        try:
            return Matrix(matrix)
        except:
            warning("ValueError for transform <%s%s>." % (label, tuple(params)))
            return Matrix((1,0,0,1,0,0))
#}}}

    def to_matrix(self):
        matrix = Matrix((1,0,0,1,0,0))
        for transform in self:
            matrix = matrix.combine(self._transform_to_matrix(transform))
        return Matrix(matrix)

    def __init__(self, transforms_notation):
        if(isinstance(transforms_notation, str)):
            if re.match(r'^ *(\w+ *\(.*?\)( +,? *|, *))*\w+ *\(.*?\) *$',
                        transforms_notation):
                transforms = re.findall(r'\w+ *\(.*?\)',
                                        transforms_notation)
                ret = []
                if transforms:
                    try:
                        for transform in transforms:
                            match_ = re.search(r'(\w+) *\((.*)\)', transform)
                            transform_type = match_.group(1)
                            try:
                                params = [float(param) for param in re.split(r' +,? *|, *', match_.group(2))]
                            except:
                                warning("Strange transform - <%s>." %
                                         transform)
                                return None
                            ret.append([transform_type, params])
                    except:
                        warning("ValueError for transform - <%s>." %
                                 transforms_notation)
                self= list.__init__(self, ret)
            else:
                warning("ValueError for transform - <%s>." %
                         transforms_notation)
        elif(isinstance(transforms_notation, list)):
            self= list.__init__(self, transforms_notation)
        elif transforms_notation is None:
            return None
        else:
            warning(type(transforms_notation))
            warning("ValueError for transform - <%s>." %
                     transforms_notation)
            return None
#}}}
class NumTuple(tuple): #{{{
    def __repr__(self):
        ret = '['
        for item in self:
            ret += "%g" % item + ', '
        return ret[:-2] + ']'

#}}}
class Color(NumTuple): #{{{
    @staticmethod
    def string_to_rgb(color_description): #{{{
        def color_value(value):
            match_=re.search(r'^(.*)%\s*$', value)
            if match_: # "100%", " 100 % " or "0.5%" etc.
                ret = float(match_.group(1))/100.
            else:
                try:
                    ret = float(value)/255.
                except:
                    ret = 0
                    warning("ValueError for rgb color value (%s)." % value)
            return ret

        colorkeywords = { # ColorKeywords {{{
            'aliceblue'           :'#F0F8FF',
            'antiquewhite'        :'#FAEBD7',
            'aqua'                :'#00FFFF',
            'aquamarine'          :'#7FFFD4',
            'azure'               :'#F0FFFF',
            'beige'               :'#F5F5DC',
            'bisque'              :'#FFE4C4',
            'black'               :'#000000',
            'blanchedalmond'      :'#FFEBCD',
            'blue'                :'#0000FF',
            'blueviolet'          :'#8A2BE2',
            'brown'               :'#A52A2A',
            'burlywood'           :'#DEB887',
            'cadetblue'           :'#5F9EA0',
            'chartreuse'          :'#7FFF00',
            'chocolate'           :'#D2691E',
            'coral'               :'#FF7F50',
            'cornflowerblue'      :'#6495ED',
            'cornsilk'            :'#FFF8DC',
            'crimson'             :'#DC143C',
            'cyan'                :'#00FFFF',
            'darkblue'            :'#00008B',
            'darkcyan'            :'#008B8B',
            'darkgoldenrod'       :'#B8860B',
            'darkgray'            :'#A9A9A9',
            'darkgreen'           :'#006400',
            'darkgrey'            :'#A9A9A9',
            'darkkhaki'           :'#BDB76B',
            'darkmagenta'         :'#8B008B',
            'darkolivegreen'      :'#556B2F',
            'darkorange'          :'#FF8C00',
            'darkorchid'          :'#9932CC',
            'darkred'             :'#8B0000',
            'darksalmon'          :'#E9967A',
            'darkseagreen'        :'#8FBC8F',
            'darkslateblue'       :'#483D8B',
            'darkslategray'       :'#2F4F4F',
            'darkslategrey'       :'#2F4F4F',
            'darkturquoise'       :'#00CED1',
            'darkviolet'          :'#9400D3',
            'deeppink'            :'#FF1493',
            'deepskyblue'         :'#00BFFF',
            'dimgray'             :'#696969',
            'dimgrey'             :'#696969',
            'dodgerblue'          :'#1E90FF',
            'firebrick'           :'#B22222',
            'floralwhite'         :'#FFFAF0',
            'forestgreen'         :'#228B22',
            'fuchsia'             :'#FF00FF',
            'gainsboro'           :'#DCDCDC',
            'ghostwhite'          :'#F8F8FF',
            'gold'                :'#FFD700',
            'goldenrod'           :'#DAA520',
            'gray'                :'#808080',
            'grey'                :'#808080',
            'green'               :'#008000',
            'greenyellow'         :'#ADFF2F',
            'honeydew'            :'#F0FFF0',
            'hotpink'             :'#FF69B4',
            'indianred'           :'#CD5C5C',
            'indigo'              :'#4B0082',
            'ivory'               :'#FFFFF0',
            'khaki'               :'#F0E68C',
            'lavender'            :'#E6E6FA',
            'lavenderblush'       :'#FFF0F5',
            'lawngreen'           :'#7CFC00',
            'lemonchiffon'        :'#FFFACD',
            'lightblue'           :'#ADD8E6',
            'lightcoral'          :'#F08080',
            'lightcyan'           :'#E0FFFF',
            'lightgoldenrodyellow':'#FAFAD2',
            'lightgray'           :'#D3D3D3',
            'lightgreen'          :'#90EE90',
            'lightgrey'           :'#D3D3D3',
            'lightpink'           :'#FFB6C1',
            'lightsalmon'         :'#FFA07A',
            'lightseagreen'       :'#20B2AA',
            'lightskyblue'        :'#87CEFA',
            'lightslategray'      :'#778899',
            'lightslategrey'      :'#778899',
            'lightsteelblue'      :'#B0C4DE',
            'lightyellow'         :'#FFFFE0',
            'lime'                :'#00FF00',
            'limegreen'           :'#32CD32',
            'linen'               :'#FAF0E6',
            'magenta'             :'#FF00FF',
            'maroon'              :'#800000',
            'mediumaquamarine'    :'#66CDAA',
            'mediumblue'          :'#0000CD',
            'mediumorchid'        :'#BA55D3',
            'mediumpurple'        :'#9370DB',
            'mediumseagreen'      :'#3CB371',
            'mediumslateblue'     :'#7B68EE',
            'mediumspringgreen'   :'#00FA9A',
            'mediumturquoise'     :'#48D1CC',
            'mediumvioletred'     :'#C71585',
            'midnightblue'        :'#191970',
            'mintcream'           :'#F5FFFA',
            'mistyrose'           :'#FFE4E1',
            'moccasin'            :'#FFE4B5',
            'navajowhite'         :'#FFDEAD',
            'navy'                :'#000080',
            'oldlace'             :'#FDF5E6',
            'olive'               :'#808000',
            'olivedrab'           :'#6B8E23',
            'orange'              :'#FFA500',
            'orangered'           :'#FF4500',
            'orchid'              :'#DA70D6',
            'palegoldenrod'       :'#EEE8AA',
            'palegreen'           :'#98FB98',
            'paleturquoise'       :'#AFEEEE',
            'palevioletred'       :'#DB7093',
            'papayawhip'          :'#FFEFD5',
            'peachpuff'           :'#FFDAB9',
            'peru'                :'#CD853F',
            'pink'                :'#FFC0CB',
            'plum'                :'#DDA0DD',
            'powderblue'          :'#B0E0E6',
            'purple'              :'#800080',
            'red'                 :'#FF0000',
            'rosybrown'           :'#BC8F8F',
            'royalblue'           :'#4169E1',
            'saddlebrown'         :'#8B4513',
            'salmon'              :'#FA8072',
            'sandybrown'          :'#F4A460',
            'seagreen'            :'#2E8B57',
            'seashell'            :'#FFF5EE',
            'sienna'              :'#A0522D',
            'silver'              :'#C0C0C0',
            'skyblue'             :'#87CEEB',
            'slateblue'           :'#6A5ACD',
            'slategray'           :'#708090',
            'slategrey'           :'#708090',
            'snow'                :'#FFFAFA',
            'springgreen'         :'#00FF7F',
            'steelblue'           :'#4682B4',
            'tan'                 :'#D2B48C',
            'teal'                :'#008080',
            'thistle'             :'#D8BFD8',
            'tomato'              :'#FF6347',
            'turquoise'           :'#40E0D0',
            'violet'              :'#EE82EE',
            'wheat'               :'#F5DEB3',
            'white'               :'#FFFFFF',
            'whitesmoke'          :'#F5F5F5',
            'yellow'              :'#FFFF00',
            'yellowgreen'         :'#9ACD32',
        }
        # }}}

        match_=re.search(r'rgb\(([^,]*),([^,]*),([^,]*)\)', color_description)
        if match_:
            '''
            rgb(,,) notation:
             e.g. rgb(255,255,255), rgb(100%,255,255) etc.
            '''
            r = color_value(match_.group(1))
            g = color_value(match_.group(2))
            b = color_value(match_.group(3))
        else:
            if re.search(r'^#[0-9a-fA-F]{6}$', color_description):
                '''#FFFFFF notation'''
                pass
            elif re.search(r'^#[0-9a-fA-F]{3}$', color_description):
                '''#FFF notation'''
                temp = ''
                for s in color_description:
                    temp += s + s
                color_description = temp[1:]
            else:
                '''string notation (ex. red, blue, black ...)'''
                try:
                    color_description = colorkeywords[color_description]
                except:
                    warning("Color name <%s> cannot be handled." % color_description)
                    color_description = '#000000'

            r = int(color_description[1:3], 16) / 255.
            g = int(color_description[3:5], 16) / 255.
            b = int(color_description[5:7], 16) / 255.
        return (r,g,b)
    #}}}
    def __init__(self, data):
        if len(data) != 4:
            raise ValueError('Color must be 4 element array ([r,g,b,a]).')
#}}}
class Vector(NumTuple):#{{{
    def en_matrix(self, matrix):
        '''The vector is transformed by matrix'''
        return Vector([matrix[0]*self[0] + matrix[2]*self[1] + matrix[4],
                       matrix[1]*self[0] + matrix[3]*self[1] + matrix[5]])

    def rotate(self, theta):
        return Vector([cos(theta)*self[0] + sin(theta)*self[1],
                      -sin(theta)*self[0] + cos(theta)*self[1]])

    def angle_between(self, other):
        '''returns angle between two Vectors. Unit: radians'''
        if isinstance(other, Vector):
            try:
                angle = acos((self[0]*other[0] + self[1]*other[1])/(abs(self)*abs(other)))
            except:
                angle = 0
            if self[0]*other[1] - self[1]*other[0] < 0:
                angle *= -1
            return angle
        else:
            raise ValueError('Strange instance')

    def __pos__(self):
        return self
    def __neg__(self):
        return Vector([-a for a in self])

    def __add__(self, other):
        if len(self) == len(other):
            return Vector([a + b for a, b in zip(self, other)])
        else:
            raise ValueError('Vector dimension error.')
    def __sub__(self, other):
        return self.__add__(-other)
    def __mul__(self, other):
        try:
            return Vector([other*a for a in self])
        except:
            raise ValueError('Strange value.')
    def __div__(self, other):
        try:
            return Vector([a/other for a in self])
        except:
            raise ValueError('Strange value.')

    def __truediv__(self, other):
        return self.__div__(other)

    def __abs__(self):
        return sqrt(sum([a*a for a in self]))
#}}}
class Vecs(list):#{{{1
    _bb_x_min = None
    _bb_x_max = None
    _bb_y_min = None
    _bb_y_max = None
    def _set_bb(self):#{{{2
        if self._bb_x_min is not None:
            return
        self._bb_x_min = self._bb_x_max = self[0][0]
        self._bb_y_min = self._bb_y_max = self[0][1]

        for x, y in self:
            if   x < self._bb_x_min:
                self._bb_x_min = x
            elif x > self._bb_x_max:
                self._bb_x_max = x
            if   y < self._bb_y_min:
                self._bb_y_min = y
            elif y > self._bb_y_max:
                self._bb_y_max = y
#}}}2
    def _current_next_pos(self, vecs): #{{{2
        point_num = len(vecs)
        for i in range(point_num):
            yield vecs[i], vecs[(i+1) % point_num]
#}}}2
    def is_include(self, point, include_on_edge=False): #{{{2
        '''
        Return True when point inside of vecs.
        When include_on_edge is True: Return True when point is on edge.
        @params point -- a survey point
        '''
        point_num = len(self)
        if point_num == 0: return False;
        if point_num == 1: return point == self[0]

        p_x, p_y = point[0], point[1]

        # On edge
        if include_on_edge:
            for (cur_x, cur_y), (next_x, next_y) in self._current_next_pos(self):
                if (
                        (   # Segment(cur-next) is horizontal
                            # and survey point exist on same height.
                            cur_y == next_y == p_y
                        and(# Survey point exists on the segment.
                                 cur_x <= p_x <= next_x
                             or next_x <= p_x <= cur_x
                            )
                        )
                     or (   # Not horizontal
                            cur_y != next_y
                        and(# y-coordinate check
                                cur_y <= p_y <= next_y
                             or next_y <= p_y <= cur_y
                            )
                            # Survey point exists on the segment.
                        and p_x == cur_x + (next_x-cur_x)*(p_y-cur_y)/(next_y-cur_y)
                        )
                    ):
                    return True;

        # Inside/outside of polygon check:
        # How meny times the point intersects with segments,
        #  when a survey point continuously moves to right.
        # Odd -> Inside (True)
        # Even -> Outside (False)
        result = False;
        for (cur_x, cur_y), (next_x, next_y) in self._current_next_pos(self):
            # Every time intersect, convert result (True <-> False)
            if (
                    (cur_y <= p_y < next_y or next_y <= p_y < cur_y) # y-coordinate check
                and (
                        (   cur_y == next_y # Segment(cur-next) is horizontal
                        and p_x < cur_x
                        )
                     or (   cur_y != next_y # Not horizontal
                        and p_x < cur_x + (p_y-cur_y)*(next_x-cur_x)/(next_y-cur_y)
                        )
                    )
                ):
                result = not result
        return result;
#}}}2
    def is_include_vecs(self, vecs): #{{{2
        self._set_bb()
        vecs._set_bb()
        if (    vecs._bb_x_min < self._bb_x_min
             or vecs._bb_x_max > self._bb_x_max
             or vecs._bb_y_min < self._bb_y_min
             or vecs._bb_y_max > self._bb_y_max
            ):
            return False
        for point in vecs:
            if not self.is_include(point):
                return False
        return True
#}}}2
#}}}1
class Surfaces(list):#{{{1
    _bb_x_min = None
    _bb_x_max = None
    _bb_y_min = None
    _bb_y_max = None
    def _set_bb(self):#{{{
        if self._bb_x_min is not None:
            return
        outside_vecs = self[0]
        outside_vecs._set_bb()
        self._bb_x_min = outside_vecs._bb_x_min
        self._bb_x_max = outside_vecs._bb_x_max
        self._bb_y_min = outside_vecs._bb_y_min
        self._bb_y_max = outside_vecs._bb_y_max
#}}}
    def is_include(self, point): #{{{2
        self._set_bb()
        # Out of BoundingBox => return False
        if (    point[0] < self._bb_x_min
             or point[0] > self._bb_x_max
             or point[1] < self._bb_y_min
             or point[1] > self._bb_y_max
            ):
            return False

        for i, vecs in enumerate(self):
            if i == 0:
                if not vecs.is_include(point, True): # outside of polygon
                    return False
            else:
                if vecs.is_include(point, False): # in hole
                    return False
        return True
#}}}2
    def is_include_vecs(self, vecs): #{{{2
        self._set_bb()
        vecs._set_bb()
        if (    vecs._bb_x_min < self._bb_x_min
             or vecs._bb_x_max > self._bb_x_max
             or vecs._bb_y_min < self._bb_y_min
             or vecs._bb_y_max > self._bb_y_max):
            return False
        for point in vecs:
            if not self.is_include(point):
                return False
        return True
#}}}2
#}}}1

class SVG_Style(dict):#{{{
    def getstroke_color(self):
        r,g,b = Color.string_to_rgb(self['stroke'])
        o = float(self['stroke-opacity'])
        o *= float(self['opacity'])
        return Color([r,g,b,o])

    def getcolor_and_drawborder(self):
        drawBorder = False
        fill = self['fill']
        if fill == 'none':
            if self['stroke'] == 'none':
                stroke = '#000000'
            else:
                stroke = self['stroke']
                drawBorder = True
            r, g, b = Color.string_to_rgb(stroke)
            o = 0
        else:
            r, g, b = Color.string_to_rgb(fill)
            o = float(self['fill-opacity'])

        o *= float(self['opacity'])

        return Color([r, g, b, o]), drawBorder

    def inherit(self, inherited_style):
        if inherited_style:
            ret = inherited_style.copy()
            ret.update(self)
            if (   'opacity' in inherited_style
               and 'opacity' in self
               ):
                ret['opacity'] = float(inherited_style['opacity']) * float(self['opacity'])
        else:
            ret = self
        return SVG_Style(ret.copy())
    def __init__(self, arg={}):
        attributes = {}
        if isinstance(arg, dict):
            attributes.update(arg)
        elif isinstance(arg, _ElementInterface):
            for attribute in ('fill', 'fill-opacity', 'stroke', 'stroke-opacity', 'opacity'):
                if arg.get(attribute):
                    attributes.update({attribute:arg.get(attribute)})
            style = arg.get('style')
            if style:
                style = re.sub(r'\s*', '', style)
                styles = {}
                for property_ in style.split(';'):
                    if not property_: continue
                    try:
                        property_name, value = property_.split(':')
                    except ValueError: # style="a" etc. (invalid style)
                        warning("ValueError for style <%s>." % style)
                        styles = {}
                        break
                    styles[property_name] = value
                attributes.update(styles)
        else:
            raise ValueError('Argument\'s instance should be dict or instance')
        self.update(attributes)
#}}}
class _D_TOKEN(object): #{{{
    NUMBER_REGEX, COMMAND_REGEX = range(2)
    __slots__ = ['NUMBER_REGEX', 'COMMAND_REGEX']
#}}}
#{{{
patterns = [
    (_D_TOKEN.NUMBER_REGEX, re.compile(r'[+-]?(\d*\.\d+|\d+\.|\d+)([eE][+-]?\d+)?')),
    (_D_TOKEN.COMMAND_REGEX, re.compile(r'[MmZzLlHhVvCcSsQqTtAa]')),
]
whitespace = re.compile('\s+')
#}}}
class SVG_Path(list): #{{{
    ###################################################
    # http://www.w3.org/TR/SVG/paths.html#PathElement #
    ###################################################
    #horizontal_lineto:               ( "H" | "h" ) wsp* coordinate
    #vertical_lineto:                 ( "V" | "v" ) wsp* coordinate

    #closepath:                       ( "Z" | "z" )

    #moveto:                          ( "M" | "m" ) wsp* coordinate_pair
    #lineto:                          ( "L" | "l" ) wsp* coordinate_pair

    #curveto:                         ( "C" | "c" ) wsp* coordinate_pair_x3
    #smooth_curveto:                  ( "S" | "s" ) wsp* coordinate_pair_x2

    #quadratic_bezier_curveto:        ( "Q" | "q" ) wsp* coordinate_pair_x2
    #smooth_quadratic_bezier_curveto: ( "T" | "t" ) wsp* coordinate_pair_x2

    #elliptical_arc:                  ( "A" | "a" ) wsp* elliptical_arc_argument
    
    def _simplify(self, list_): #{{{2
        '''
        Comvert h-command to L-command
        Comvert H-command to L-command
        Comvert v-command to L-command
        Comvert V-command to L-command
        Comvert z-command to L-command
        Comvert Z-command to L-command
        
        Comvert lower-case-command to UPPER-case-command
        '''
        if list_ == []:
            return []
        ret = []

        current_point = Vector([0, 0])
        initial_point = current_point
        while list_:
            parameters = list_.pop(0)
            command = parameters.pop(0)

            if   command == 'H':
                command = 'L'
                parameters = [parameters[0],
                                 current_point[1]]
            elif command == 'h':
                command = 'L'
                parameters = [current_point[0]+parameters[0],
                                 current_point[1]]
            elif command == 'V':
                command = 'L'
                parameters = [current_point[0],
                                 parameters[0]]
            elif command == 'v':
                command = 'L'
                parameters = [current_point[0],
                                 current_point[1]+parameters[0]]
            elif re.match(r'[Zz]', command):
                command = 'L'
                parameters = [initial_point[0],
                                 initial_point[1]]
            ##########

            if re.match(r'[ML]', command):
                current_point = Vector((parameters[0], parameters[1]))
                ret.append([command, current_point])
                if command == 'M':
                    initial_point = current_point
            elif re.match(r'[ml]', command):
                current_point += Vector((parameters[0], parameters[1]))
                ret.append([command.upper(), current_point])
                if command == 'm':
                    initial_point = current_point

            # The cubic Bezier curve commands
            elif command == 'C':
                p1 = Vector((parameters[0], parameters[1]))
                p2 = Vector((parameters[2], parameters[3]))
                current_point = Vector((parameters[4], parameters[5]))
                ret.append(['C', p1, p2, current_point])
            elif command == 'c':
                p1 = current_point + Vector((parameters[0], parameters[1]))
                p2 = current_point + Vector((parameters[2], parameters[3]))
                current_point += Vector((parameters[4], parameters[5]))
                ret.append(['C', p1, p2, current_point])
            elif re.match(r'[Ss]', command):
                if ret[-1][0] == 'C':
                    p1 = current_point * 2 - ret[-1][2]
                else:
                    p1 = current_point
                if command == 'S':
                    p2 = Vector((parameters[0], parameters[1]))
                    current_point = Vector((parameters[2], parameters[3]))
                else:
                    p2 = current_point + Vector((parameters[0], parameters[1]))
                    current_point += Vector((parameters[2], parameters[3]))
                ret.append(['C', p1, p2, current_point])

            # The quadratic Bezier curve commands
            elif re.match(r'[Q]', command):
                p1 = Vector((parameters[0], parameters[1]))
                current_point = Vector((parameters[2], parameters[3]))
                ret.append([command, p1, current_point])
            elif re.match(r'[q]', command):
                p1 = current_point + Vector((parameters[0], parameters[1]))
                current_point += Vector((parameters[2], parameters[3]))
                ret.append([command.upper(), p1, current_point])
            elif re.match(r'[Tt]', command):
                if ret[-1][0] == 'Q':
                    p1 = current_point * 2 - ret[-1][1]
                else:
                    p1 = current_point
                if command == 'T':
                    current_point = Vector((parameters[0], parameters[1]))
                else:
                    current_point += Vector((parameters[0], parameters[1]))
                ret.append(['Q', p1, current_point])

            #The elliptical arc curve commands
            elif re.match(r'[Aa]', command):
                rx = abs(parameters[0])
                ry = abs(parameters[1])
                x_axis_rotation = parameters[2]
                large_arc_flag = parameters[3]
                sweep_flag = parameters[4]
                if command == 'A':
                    current_point = Vector((parameters[5], parameters[6]))
                else:
                    current_point += Vector((parameters[5], parameters[6]))
                ret.append(['A', rx, ry, x_axis_rotation,
                            large_arc_flag, sweep_flag, current_point])
            else:
                assert False

        return ret
#}}}2
    def _tokens_to_list(self, tokens): #{{{2
        '''
        NOTE: This fucntion change implicit command into explicit command.
              e.g "M 0 5 10 20 30 40" 
                  -> [['M', [0, 5]], ['L', [10, 20]], ['L', [30, 40]]]
        '''
        last_command = ''
        command_require_num = {
                'M':2,
                'm':2,
                'Z':0,
                'z':0,
                'L':2,
                'l':2,
                'H':1,
                'h':1,
                'V':1,
                'v':1,
                'C':6,
                'c':6,
                'S':4,
                's':4,
                'Q':4,
                'q':4,
                'T':2,
                't':2,
                'A':7,
                'a':7,
                }
        ret = []
        if 'm' != tokens[0][1] != 'M':
            warning("Strange path.")
            return []
        while tokens:
            sequence = []
            if tokens[0][0] == _D_TOKEN.COMMAND_REGEX:
                command = tokens[0][1]
                del tokens[0]
            else:
                if   last_command == 'M':
                    last_command = 'L'
                elif last_command == 'm':
                    last_command = 'l'
                elif (    last_command == 'z'
                       or last_command == 'Z'
                      ):
                    # e.g. "M 1 0 z 1 0" is not correct path.
                    warning("Strange path.")
                    break
                elif last_command == '':
                    warning("Strange path.")
                    return []
                command = last_command
            sequence.append(command)
            for i in range(command_require_num[command]):
                if tokens[0][0] != _D_TOKEN.NUMBER_REGEX:
                    warning("Strange path.")
                    return []
                sequence.append(float(tokens[0][1]))
                del tokens[0]
            last_command=command
            
            ret.append(sequence)
        return ret
#}}}2
    def _tokenize(self, string_): #{{{2
        string_ = string_.replace(',', ' ')
        ret = []
        while string_:
            match_ = whitespace.match(string_)
            if match_:
                # Remove ^\s+ in strings_
                #  e.g. "  M 0 1" -> "M 0 1"
                string_ = string_[match_.end():]
                if not string_:
                    break

            hasMatched = False
            for tokentype, pattern in patterns:
                match_ = pattern.match(string_)
                if match_:
                    hasMatched = True
                    ret.append([tokentype, match_.group(0)])
                    string_ = string_[match_.end():]
                    break
            if not hasMatched:
                warning("Strange path! %s" % string_)
                return None
        return ret
#}}}2

    def __init__(self, string_):
        tokens = self._tokenize(string_)
        if tokens is None:
            return None
        list_ = self._tokens_to_list(tokens)
        if list_ == []:
            return None
        self.extend(self._simplify(list_))
#}}}

class _PhunObject(dict):#{{{
    default = {}
    _default = {
            'color':[random(), random(), random(), 1], #FIXME
            #'entityID':1, #FIXME
            #'zDepth':1.0, #FIXME
            }
    def __str__(self):
        temp = "Scene.add%s {\n" % self.__class__.__name__
        for key, value in self.items():
            if isinstance(value, str):
                if(value != '+inf'):
                    value = '''"%s"''' % value
            elif isinstance(value, bool):
                if value:
                    value = 'true'
                else:
                    value = 'false'
            elif isinstance(value, float):
                value = "%g" % value
            temp += "    %s := %s;\n" % (key, value)
        temp += '};'
        return temp

    def __repr__(self):
        return "<%s at %x>" % (self.__class__.__name__, id(self))

    def __init__(self, attrib):
        if not MINIMUM_MODE:
            self.update(self.default)
        self.update(attrib)
#}}}

class _PhunGeometry(_PhunObject): #{{{
    default = _PhunObject._default.copy()
    default.update({ #{{{2
            'airFrictionMult':1.0,
            'angle':0.0,
            'attraction':0.0,
            'collideSet':1,
            'collideWater':True,
            'controllerAcc':11.0,
            'controllerInvertX':False,
            'controllerInvertY':False,
            'controllerReverseXY':False,
            'density':2.0,
            'drawBorder':True,
            'friction':0.5,
            #'geomID':1, #FIXME
            'heteroCollide':False,
            'immortal':False,
            'inertiaMultiplier':1.0,
            'killer':False,
            'materialVelocity':0.0,
            'onCollide':'(elem)=>{}',
            'onHitByLaser':'(elem)=>{}',
            'opaqueBorders':True,
            'pos':[0.0, 0.0],
            'vel':[0.0, 0.0],
            'reflectiveness':1.0,
            'refractiveIndex':1.5,
            'restitution':0.5,
            'showForceArrows':False,
            'showVelocity':False,
            'textColor':[1.0, 1.0, 1.0, 1.0],
            'textConstrained':True,
            'textFont':'Verdana',
            'textFontSize':32.0,
            'textScale':0.5,
            'texture':'',
            'textureMatrix':[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            })
    #}}}2
    def getrelpos(self, point): #{{{
        return (point-self['pos']).rotate(self['angle'])
#}}}
#}}}
class Polygon(_PhunGeometry): #{{{1
    _area = None
    _bb_x_min = None
    _bb_x_max = None
    _bb_y_min = None
    _bb_y_max = None

    default = _PhunGeometry._default.copy()
    default.update({
            })

    def _set_bb(self):#{{{
        if self._bb_x_min is not None:
            return
        outside_vecs = self['surfaces'][0]
        outside_vecs._set_bb()
        self._bb_x_min = outside_vecs._bb_x_min
        self._bb_x_max = outside_vecs._bb_x_max
        self._bb_y_min = outside_vecs._bb_y_min
        self._bb_y_max = outside_vecs._bb_y_max

#}}}
    def _getcenterpos_and_area_of_vecs(self, vecs): #{{{
        #@return barycentric coordinates and area
        partial_area, area_sum = 0, 0;
        center_pos = Vector((0, 0));

        for i in range(1, len(vecs)-1):
            # Exterior product of (vecs[0]-vecs[i]) and (vecs[0]-vecs[i+1]) equals
            # signed area of triangle (vec[0], vec[i], vec[i+1]) * 2
            partial_area = (
                    (vecs[i][0] - vecs[0][0]) * (vecs[i+1][1] - vecs[0][1]) -
                    (vecs[i][1] - vecs[0][1]) * (vecs[i+1][0] - vecs[0][0])
                    )/2.
            partial_center = (vecs[0] + vecs[i] + vecs[i+1]) / 3.;
            area_sum += partial_area;

            center_pos += partial_center * partial_area;
        if area_sum != 0:
            center_pos /= area_sum;
        return (center_pos, abs(area_sum));
        #}}}
    def _set_pos_and_area(self):#{{{
        surfaces = self['surfaces']
        each_pos = []
        each_area = []
        area = 0
        for i, vecs in enumerate(surfaces):
            temp_pos, temp_area = self._getcenterpos_and_area_of_vecs(vecs)
            if i != 0:
                temp_area = -temp_area
            each_pos.append(temp_pos)
            each_area.append(temp_area)
            area += temp_area

        pos = Vector((0, 0))
        if area != 0:
            for temp_pos, temp_area in zip(each_pos, each_area):
                pos += temp_pos * temp_area
            pos /= area

        self.update({'pos':pos})
        self._area = area
#}}}
    def is_include(self, point): #{{{2
        pos = self['pos']
        point_rotated = pos + (point-pos).rotate(self['angle'])
        self._set_bb()
        if (   point_rotated[0] < self._bb_x_min
            or point_rotated[0] > self._bb_x_max
            or point_rotated[1] < self._bb_y_min
            or point_rotated[1] > self._bb_y_max
            ):
            return False

        for i, vecs in enumerate(self['surfaces']):
            if i == 0:
                if not vecs.is_include(point_rotated, True):
                    # outside of polygon
                    return False
            else:
                if vecs.is_include(point_rotated, False):
                    # in hole
                    return False
        return True
#}}}2
    def is_include_polygon(self, polygon): #{{{2
        self._set_bb()
        polygon._set_bb()
        if (    polygon._bb_x_max < self._bb_x_min
             or polygon._bb_x_min > self._bb_x_max
             or polygon._bb_y_max < self._bb_y_min
             or polygon._bb_y_min > self._bb_y_max
            ):
            return False
        for vecs in polygon['surfaces']:
            for point in vecs:
                if not self.is_include(point):
                    return False
        return True
#}}}2

    def __init__(self, attrib):
        _PhunGeometry.__init__(self, attrib)
        self._set_pos_and_area()
#}}}1
class Box(_PhunGeometry): #{{{1
    default = _PhunGeometry._default.copy()
    default.update({
            'size':[1,0, 1,0],
            'text':'',
            'ruler':False,
            })

    def is_include(self, point): #{{{
        pos = self['pos']
        size = self['size']
        min_ = pos - size/2.
        max_ = pos + size/2.
        point_rotated = pos + (point-pos).rotate(self['angle'])
        if (    min_[0] < point_rotated[0] < max_[0] 
            and min_[1] < point_rotated[1] < max_[1]
            ):
            return True
#}}}
    def __init__(self, attrib):
        _PhunGeometry.__init__(self, attrib)
#}}}1
class Circle(_PhunGeometry): #{{{1
    def is_include(self, point): #{{{
        return self['radius'] > abs(self['pos']-point)
#}}}
    default = _PhunGeometry._default.copy()
    default.update({
            'drawCake':True,
            'radius':1.0,
            })
    def __init__(self, attrib):
        _PhunGeometry.__init__(self, attrib)
#}}}1
class Plane(_PhunGeometry): #{{{1
    default = _PhunGeometry._default.copy()
    default.update({
            })

    def is_include(self, point): #{{{
        pos = self['pos']
        point_rotated = pos + (point-pos).rotate(self['angle'])
        return point_rotated[0] < pos[0]
#}}}

    def __init__(self, attrib):
        _PhunGeometry.__init__(self, attrib)
#}}}1

class _PhunAttachment(_PhunObject):#{{{
    default = _PhunObject._default.copy()
    default.update({
            'size':0.1,
            #'opaqueBorders':True,
            })
    def _try_attatch_between2geom(self, phun_objects): #{{{2
        '''
        @param phun_objects object list (include "self"). Back to front order
        '''
        self_index = None
        for i, o in enumerate(phun_objects):
            if o is self:
                self_index = i

        o0, o1 = None, None
        o0_found = o1_found = False
        geom0pos = self.pop('geom0pos')
        geom1pos = self.pop('geom1pos')
        o0_index = None
        # {{{ o0
        for i in range(self_index-1, -1, -1):
            o0 = phun_objects[i]
            if not isinstance(o0, _PhunGeometry): continue
            if o0.is_include(geom0pos):
                self['geom0'] = o0['geomID']
                self['geom0pos'] = o0.getrelpos(geom0pos)
                o0_index = i
                o0_found = True
                break
        # }}}

        # {{{ o1
        for i in range(self_index-1, -1, -1):
            if (i == o0_index):
                continue
            o1 = phun_objects[i]
            if not isinstance(o1, _PhunGeometry): continue
            if o1.is_include(geom1pos):
                self['geom1'] = o1['geomID']
                self['geom1pos'] = o1.getrelpos(geom1pos)
                o1_found = True
                break
        # }}}

        if (    o0_found 
            and o1_found
            ):
            return True
        elif (    not o0_found
              and not o1_found
              ):
            return False
        else:
            if o0_found:
                self['geom1'] = 0
                self['geom1pos'] = geom1pos
                #o_geom = o0
            elif o1_found:
                self['geom0'] = 0
                self['geom0pos'] = geom0pos
                #o_geom = o1
            else:
                assert False
# Script below is for Algodoo's spring constant
#            if isinstance(self, Spring):
#                if isinstance(o_geom, Polygon):
#                    self['constant'] = 10 * o_geom._area
#                elif isinstance(o_geom, Box):
#                    self['constant'] = 10 * o_geom["size"][0] * o_geom["size"][1]
#                elif isinstance(o_geom, Circle):
#                    self['constant'] = 10 * 2 * pi * o_geom["radius"]**2
            return True
#}}}2
#}}}
class Spring(_PhunAttachment):#{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'geom0':0,
            'geom0pos':[0.0, 0.0],
            'geom1':0,
            'geom1pos':[0.0, 0.0],
            'dampingFactor':0.1,
            'legacyMode':2,
            'length':0.0,
            'constant':0.1,
            })
    def try_attatch(self, phun_objects):
        return self._try_attatch_between2geom(phun_objects)
#}}}
class Fixjoint(_PhunAttachment):#{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'geom0':-1,
            'world0pos':[0, 0],
            'geom1':0,
            'geom1ps':[0, 0],
            })
#}}}
class Hinge(_PhunAttachment):#{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'geom0':-1,
            'world0pos':[0, 0],
            'geom1':-1,
            'world1pos':[0, 0],
            'ccw':False,
            'motorTorque':100.0,
            'impulseLimit':"+inf",
            'autoBrake':False,
            'motor':False,
            'motorSpeed':1.5707964,
            'distanceLimit':"+inf",
            'buttonForward' : "",
            'buttonBack' : "",
            'buttonBrake' : "",
            })
    def try_attatch(self, phun_objects): #{{{2
        return self._try_attatch_between2geom(phun_objects)
#}}}2
#}}}
class Pen(_PhunAttachment): #{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'fadeTime':1.5,
            'geom':1,
            'relPoint':Vector([0, 0]),
            'rotation':0
            })

    def try_attatch(self, phun_objects):
        return True #FIXME
#}}}
class LaserPen(_PhunAttachment): #{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'geom':0,
            'cutter':False,
            'collideSet':127,
            'collideWater':True,
            'onLaserHit':"(elem)=>{}",
            'pos':Vector([0, 0]),
            'velocity':"+inf",
            'fadeDist':25.0,
            'maxRays':1000,
            'showLaserBodyAttrib':True,
            'rotation':0.0
            })
    def try_attatch(self, phun_objects):
        return True #FIXME
#}}}
class Thruster(_PhunAttachment): #{{{
    default = _PhunAttachment._default.copy()
    default.update({
            'geom':0,
            'pos':Vector([0, 0]),
            'maxRays':1000,
            'opaqueBorders':True,
            'followGeometry':True,
            'rotation':0.0
            })
    def try_attatch(self, phun_objects):
        return True #FIXME
#}}}

def reduce_nodes(path, allowed_angle=ALLOWED_ANGLE): #{{{
    ret = [path[0], path[1]]
    temp = ret[-1] - ret[-2]
    for i in range(2, len(path)):
        if abs(temp.angle_between(path[i] - ret[-1])) < allowed_angle:
            del ret[-1]
            ret.append(path[i]);
        else:
            ret.append(path[i]);
            temp = ret[-1] - ret[-2]
    return ret

# ========================================
def quadratic_bezier_to_path(p1, p2, p3, nodes=NODES_PER_BEZIER): #{{{
    '''
    Comvert quadratic bezier curve into path
    @params p1: Start point (Vector class)
    @params p2: Control point (Vector class)
    @params p3: End point (Vector class)
    @params nodes (int type): Larger value means more accrate
    '''
    ret = []
    for i in range(0, nodes + 1):
        t = float(i) / nodes
        temp  = p1 * ((1-t)**2)
        temp += p2 * (2 * t * (1-t))
        temp += p3 * (t**2)
        ret.append(Vector(temp))
    return reduce_nodes(ret)
#}}}
def cubic_bezier_to_path(p1, p2, p3, p4, nodes=NODES_PER_BEZIER): #{{{
    '''
    Comvert cubic bezier curve into path
    @params p1: Start point (Vector class)
    @params p2: First control point (Vector class)
    @params p3: Second control point (Vector class)
    @params p4: End point (Vector class)
    @params nodes (int type): Larger value means more accrate
    '''
    ret = []
    for i in range(0, nodes + 1):
        t = float(i) / nodes
        temp  = p1 * ((1-t)**3)
        temp += p2 * (3 * t * (1-t)**2)
        temp += p3 * (3 * t**2 * (1-t))
        temp += p4 * (t**3)
        ret.append(Vector(temp))
    return reduce_nodes(ret)
#}}}
def elliptical_arc_to_path(p1, rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, p2, arc_nodes_frequency=ARC_NODES_FREQUENCY): #{{{
    if rx == 0 or ry == 0: return [p1, p2]
    if rx < 0: rx *= -1
    if ry < 0: ry *= -1

    x_axis_rotation *= -pi/180.
    if large_arc_flag != 0:
        large_arc_flag = 1
    if sweep_flag != 0:
        sweep_flag = 1

    p_ = ((p1-p2)/2).rotate(-x_axis_rotation)
    temp = p_[0]**2/rx**2 + p_[1]**2/ry**2
    if temp > 1:
        sqrt_temp = sqrt(temp)
        rx *= sqrt_temp
        ry *= sqrt_temp

    try:
        c_ = Vector((rx*p_[1]/ry, -ry*p_[0]/rx)) * sqrt(abs((rx*ry)**2-(rx*p_[1])**2-(ry*p_[0])**2)/((rx*p_[1])**2+(ry*p_[0])**2))
    except:
        c_ = Vector((0, 0))
    if large_arc_flag == sweep_flag: c_ *= -1

    c = c_.rotate(x_axis_rotation) + (p1 + p2)/2

    temp1 = Vector((( p_[0] - c_[0])/rx, ( p_[1] - c_[1])/ry))
    temp2 = Vector(((-p_[0] - c_[0])/rx, (-p_[1] - c_[1])/ry))
    theta1 = Vector((1, 0)).angle_between(temp1)
    delta_theta = temp1.angle_between(temp2) % (2 * pi)
    if sweep_flag == 0 and delta_theta > 0:
        delta_theta -= 2*pi
    elif sweep_flag == 1 and delta_theta < 0:
        delta_theta += 2*pi

    ret = []
    nodes = abs(int(delta_theta / arc_nodes_frequency))
    if nodes == 0: nodes = 1
    for i in range(0, nodes + 1):
        theta = float(i) / nodes * delta_theta + theta1
        p = Vector((rx*cos(theta), ry*sin(theta))).rotate(x_axis_rotation) + c
        ret.append(p)
    return reduce_nodes(ret)
#}}}

def intersection(p1, p2, p3, p4): #{{{
    '''
    Calculate the intersect point of two segments (p1-p2 and p3-p4)
    @return intersection coordinate (Vector class)
            If intersection is none or countless -> return None
    '''

    # Clearly doesn't cross (need not to solve simultaneous equations)
    if p3[0] < p4[0]: # x coordinate order: 1234, 2134, etc. -> clearly doesn't intersect
        if (    (p3[0] > p1[0] and p3[0] > p2[0])
             or (p4[0] < p1[0] and p4[0] < p2[0])):
            return None
    else:
        if (    (p4[0] > p1[0] and p4[0] > p2[0])
             or (p3[0] < p1[0] and p3[0] < p2[0])):
            return None
    if p3[1] < p4[1]: # Same for y coordinate
        if (    (p3[1] > p1[1] and p3[1] > p2[1])
             or (p4[1] < p1[1] and p4[1] < p2[1])):
            return None
    else:
        if (    (p4[1] > p1[1] and p4[1] > p2[1])
             or (p3[1] < p1[1] and p3[1] < p2[1])):
            return None

    if p1 == p3 or p1 == p4: return p1
    if p2 == p3 or p2 == p4: return p2

    # Calculate intersection
    a = p2[1] - p1[1]
    b = p1[0] - p2[0]
    c = p4[1] - p3[1]
    d = p3[0] - p4[0]
    delta = a*d - b*c
    if delta == 0: return None # Parallel

    p = p1[0]*p2[1] - p1[1]*p2[0]
    q = p3[0]*p4[1] - p3[1]*p4[0]

    x = float( d*p - b*q) / delta
    y = float(-c*p + a*q) / delta

    # Intersection doesn't exist on segment p1-p2
    if p1[0] != p2[0]:
        if (    (x < p1[0] and x < p2[0])
             or (x > p1[0] and x > p2[0])):
            return None
    else:
        if (    (y < p1[1] and y < p2[1])
             or (y > p1[1] and y > p2[1])):
            return None
    # Intersection doesn't exist on segment p3-p4
    if p3[0] != p4[0]:
        if (    (x < p3[0] and x < p4[0])
             or (x > p3[0] and x > p4[0])):
            return None
    else:
        if (    (y < p3[1] and y < p4[1])
             or (y > p3[1] and y > p4[1])):
            return None

    # Intersection exists on both segments (p1-p2 and p3-p4)
    return Vector((x, y))
#}}}
def opposite_side(p1, p2, p3, p4, p5):#{{{
    """
    As half lines(p2-p1 and p2-p3) boundary,
    p4 and p5 exist opposite side -> return True
    p4 and p5 exist same side -> return False
    p4 and/or p5 exists on half line(p2-p1 or p2-p3) -> return False
    """
    p21 = p1 - p2
    p23 = p3 - p2
    p24 = p4 - p2
    p25 = p5 - p2
    angle123 = p21.angle_between(p23)
    if angle123 < 0: angle123 += 2 * pi
    angle124 = p21.angle_between(p24)
    if angle124 < 0: angle124 += 2 * pi
    angle125 = p21.angle_between(p25)
    if angle125 < 0: angle125 += 2 * pi

    if (    (0 < angle124 < angle123 < angle125
          or 0 < angle125 < angle123 < angle124)):
        return True
    else:
        return False
#}}}
def solve_self_intersection(received_vecs): #{{{
    if len(received_vecs) < 4: return received_vecs
    vecs = received_vecs[:]

    ret = [vecs.pop(0), vecs.pop(0), vecs.pop(0)]
    while vecs:
        p_last = ret[-1]
        p_next = vecs.pop(0)
        i = len(ret)-3
        # Calculate all cross points #{{{2
        cross_points = {}
        while i >= 0:
            p_i = ret[i]
            p_j = ret[i+1]
            p_cross = intersection(p_i, p_j, p_last, p_next)

            if (    (p_cross and p_cross != p_next)
                and (
                        (    p_cross != p_i
                        and (
                                # Simple intersection: 1 segment(i-j) & 1 segment (last-next)
                                p_cross != p_last
                                # p_last == p_cross: 1 segment(i-j) & 2 segment(ret[-2]-last-next)
                             or opposite_side(p_i, p_cross, p_j, ret[-2], p_next)
                            )
                        )
                     or (    p_cross == p_i
                        and (
                                # 2 segment(ret[i-1]-i-j) & 1 segment(last-next) intersect
                                (p_cross != p_last and opposite_side(ret[i-1], p_i, p_j, p_last, p_next))
                                # 2 segment(ret[i-1]-i-j) & 1 segment(ret[-2]-last-next) intersect
                             or (p_cross == p_last and opposite_side(ret[i-1], p_i, p_j, ret[-2], p_next))
                            )
                        )
                    )
                ):
                cross_points[i] = p_cross
                if p_cross == p_i:
                    i -= 1
            i -= 1
        #}}}2
        if cross_points == {}:
            ret.append(p_next)
            continue
        sorted_cross_points = list(cross_points.items())
        sorted_cross_points.sort(key=lambda x:abs(x[1]-p_next), reverse=True)
        indexed_points = [(i, vec) for i, vec in enumerate(ret)]
        while sorted_cross_points:
            index, p_cross = sorted_cross_points.pop(0)
            k=0
            for i in range(len(indexed_points)-1):
                if (    
                        (    indexed_points[i  ][0] == index
                         and indexed_points[i+1][0] == index + 1)
                     or (    indexed_points[i  ][0] == index + 1
                         and indexed_points[i+1][0] == index)
                    ):
                    k = i
                    break
            temp = indexed_points[:k+1]
            temp.append((-1, p_cross))
            rest = indexed_points[k+1:]
            rest.reverse()
            temp.extend(rest)
            temp.append((-1, p_cross))
            indexed_points = temp
        ret = [indexed_point[1] for indexed_point in indexed_points]
        for i in range(len(ret)-2, -1, -1):
            if (ret[i] == ret[i+1]):
                del ret[i]

        ret.append(p_next)
    return ret
#}}}

# ========================================
# Parsers
# ========================================
def parse_text(elem, matrix, style): # {{{
    #attributes = {}
    #return Box(attributes)
    return None
# }}}

def parse_path(elem, matrix, style): #{{{
    '''Comvert path into Polygon or Circle'''
    # If perfect circle -> parse as circle. {{{2
    type_ = elem.get(SODIPODI + 'type')
    if(type_ == 'arc'):
        rx = elem.get(SODIPODI + 'rx')
        ry = elem.get(SODIPODI + 'ry')

        start = elem.get(SODIPODI + 'start')
        end = elem.get(SODIPODI + 'end')
        if(    rx == ry 
           and not start
           and not end
           and abs(matrix[0]) == abs(matrix[3])
           and abs(matrix[1]) == abs(matrix[2])
           ):
            # This element is perfect circle
            cx = elem.get(SODIPODI + 'cx', 0)
            cy = elem.get(SODIPODI + 'cy', 0)
            elem.set('cx', cx)
            elem.set('cy', cy)
            elem.set('r', rx)
            return [parse_circle(elem, matrix, style)]
    #}}}2

    d__ = SVG_Path(elem.get('d', ''))
    if d__ == []:
        return []

    ret = []
    vecs_list = []

    # Convert (smooth)SVG path into vecs {{{2
    while d__:
        current_command_sequence = d__.pop(0)
        if current_command_sequence[0] == 'M':
            vecs = [current_command_sequence[1]]
        elif current_command_sequence[0] == 'Z':
            # FIXME
            pass
        else:
            assert False

        if not d__: break
        if 'M' != d__[0][0] != 'Z':
            while d__ and 'M' != d__[0][0] != 'Z':
                current_command_sequence = d__.pop(0)
                if current_command_sequence[0] == 'L':
                    vecs.append(current_command_sequence[1])
                elif current_command_sequence[0] == 'C':
                    vecs.extend(cubic_bezier_to_path(vecs[-1], *current_command_sequence[1:]))
                elif current_command_sequence[0] == 'Q':
                    vecs.extend(quadratic_bezier_to_path(vecs[-1], *current_command_sequence[1:]))
                elif current_command_sequence[0] == 'A':
                    vecs.extend(elliptical_arc_to_path(vecs[-1], *current_command_sequence[1:]))
                else:
                    assert False
            # Remove overlapping points
            for i in range(len(vecs)-2, -1, -1):
                if vecs[i] == vecs[i+1]:
                    del vecs[i]
            if   len(vecs) <= 1:
                pass
            elif len(vecs) == 2:
                elem.set('x1', vecs[0][0])
                elem.set('y1', vecs[0][1])
                elem.set('x2', vecs[1][0])
                elem.set('y2', vecs[1][1])
                ret.append(parse_line(elem, matrix, style))
            else:
                if vecs[-1] != vecs[0]:
                    vecs.append(vecs[0])
                vecs = solve_self_intersection(vecs)
                vecs = [point.en_matrix(matrix) for point in vecs]
                vecs_list.append(Vecs(vecs))
#}}}2

    color, drawBorder = style.getcolor_and_drawborder()
    if len(vecs_list) == 0:
        return ret
    elif len(vecs_list) == 1: # Simple path {{{2
        attributes = {
                'angle':0,
                'color':color,
                'drawBorder':drawBorder,
                'surfaces':vecs_list,
                }
        ret.append(Polygon(attributes))
        return ret
    #}}}2
    else: # Compound path {{{2
        surfaces_list = []
        while vecs_list:
            current_surface = Surfaces([vecs_list.pop(0)])
            surfaces_extend_list = []
            delete_list=[]
            append_flag = True
            for i, surface in enumerate(surfaces_list):
                if surface.is_include_vecs(current_surface[0]):
                    temp_surfaces = [surface[0]]
                    for vecs in surface[1:]:
                        if current_surface.is_include_vecs(vecs):
                            surfaces_extend_list.append(Surfaces([vecs]))
                        else:
                            temp_surfaces.append(vecs)
                    temp_surfaces.append(current_surface[0])
                    surfaces_list[i] = Surfaces(temp_surfaces)
                    append_flag = False
                    break
                elif current_surface.is_include_vecs(surface[0]):
                    current_surface.append(surface[0])
                    vecs_list.extend(surface[1:])
                    delete_list.append(i)
            while delete_list:
                del(surfaces_list[delete_list.pop()])
            if append_flag:
                surfaces_extend_list.append(current_surface)
            surfaces_list.extend(surfaces_extend_list)
        for surfaces in surfaces_list:
            ret.append(Polygon({'angle':0, 'color':color, 'drawBorder':drawBorder, 'surfaces':surfaces}))
        return ret
    #}}}2
#}}}1
def parse_polygon(elem, matrix, style): #{{{
    '''Comvert polygon into Polygon'''
    points = elem.get('points', 0)
    d = "M" + points + "Z"
    elem.set('d', d)

    return parse_path(elem, matrix, style)[0]
#}}}
def parse_rect(elem, matrix, style): #{{{
    x = float(elem.get('x', 0))
    y = float(elem.get('y', 0))
    width  = float(elem.get('width', 0))
    height = float(elem.get('height', 0))

    try: rx = float(elem.get('rx'))
    except: rx = None
    try: ry = float(elem.get('ry'))
    except: ry = None
    if (    (rx and ry != 0) 
         or (ry and rx != 0)
        ):
        # Rounded rectangle -> parse as path
        if not rx: rx = ry
        if not ry: ry = rx
        width2 = width - 2*rx
        height2 = height - 2*ry
        d  = "m %lf,%lf " % ((x+rx), y);
        d += "l %lf,0 " %  width2;
        d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry,  rx, ry);
        d += "l 0,%lf " %  height2;
        d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry, -rx, ry);
        d += "l %lf,0 " % -width2;
        d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry, -rx,-ry);
        d += "l 0,%lf " % -height2;
        d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry,  rx,-ry);
        elem.set('d', d)
        return parse_path(elem, matrix, style)[0]

    if matrix[0]*matrix[2] != -matrix[1]*matrix[3]:
        # Parallelogram -> parse as path
        p0x, p0y = x,       y
        p1x, p1y = x+width, y
        p2x, p2y = x+width, y+height
        p3x, p3y = x,       y+height
        d = "M %lf,%lf %lf,%lf %lf,%lf %lf,%lf z" % (p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y)
        elem.set('d', d)
        return parse_path(elem, matrix, style)[0]

    pos = Vector([x+width/2., y+height/2.]).en_matrix(matrix)
    size = Vector([abs(Vector([x+width, y]).en_matrix(matrix) - Vector([x,y]).en_matrix(matrix)),
                   abs(Vector([x,y+height]).en_matrix(matrix) - Vector([x,y]).en_matrix(matrix)) ])
    angle = atan2(matrix[1], matrix[0])

    color, drawBorder = style.getcolor_and_drawborder()
    attributes = {
            'angle':angle,
            'color':color,
            'drawBorder':drawBorder,
            'pos':pos,
            'size':size,
            }
    return Box(attributes)
#}}}
def parse_ellipse(elem, matrix, style):#{{{
    cx = float(elem.get('cx', 0))
    cy = float(elem.get('cy', 0))
    rx = float(elem.get('rx'))
    ry = float(elem.get('ry'))

    if(    rx == ry
       and abs(matrix[0]) == abs(matrix[3])
       and abs(matrix[1]) == abs(matrix[2])
       ):
        elem.set('r', rx)
        return parse_circle(elem, matrix, style)
    d  = "m %lf,%lf" % (cx,cy-ry);
    d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry,  rx, ry);
    d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry, -rx, ry);
    d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry, -rx,-ry);
    d += "a %lf,%lf 0, 0,1 %lf,%lf"  % (rx,ry,  rx,-ry);
    elem.set('d', d)
    return parse_path(elem, matrix, style)[0]
#}}}
def parse_circle(elem, matrix, style): #{{{
    cx = float(elem.get('cx', 0))
    cy = float(elem.get('cy', 0))
    r  = float(elem.get('r'))

    if (    abs(matrix[0]) != abs(matrix[3]) 
         or abs(matrix[1]) != abs(matrix[2])):
        # Transform(matrix) comverts circle into ellipse
        elem.set('rx', r)
        elem.set('ry', r)
        return parse_ellipse(elem, matrix, style)

    pos = Vector([cx, cy]).en_matrix(matrix)
    radius = r * abs(sqrt(matrix[0]**2 + matrix[1]**2))
    angle = atan2(matrix[1], matrix[0])
    color, drawBorder = style.getcolor_and_drawborder()

    if('filter' in style and style['filter'] != 'none'):
        # Comvert circle with filter into Pen (tracer)
        attributes = {
                'pos':pos,
                'size':radius*2,
                'color':color,
                }
        return Pen(attributes)

    if (    ('marker-mid'   in style and style['marker-mid']   != 'none')
         or ('marker-start' in style and style['marker-start'] != 'none')
        ):
        # Comvert circle with marker-mid or marker-start into Hinge
        if 'marker-start' in style and style['marker-start'] != 'none':
            motor = True
        else:
            motor = False
        if matrix[0] == matrix[3]:
            ccw = False
        else:
            ccw = True

        color = style.getstroke_color()
        attributes = {
                'motor':motor,
                'ccw':ccw,
                'geom0pos':pos,
                'geom1pos':pos,
                'color':color,
                'size':radius*2,
                }
        return Hinge(attributes)

    attributes = {
            'angle':angle,
            'color':color,
            'drawBorder':drawBorder,
            'drawCake':False,
            'pos':pos,
            'radius':radius,
            }
    return Circle(attributes)
#}}}

def parse_line(elem, matrix, style): #{{{
    '''Comvert line into Spring or LaserPen'''
    color = style.getstroke_color()

    x1 = float(elem.get('x1', 0))
    y1 = float(elem.get('y1', 0))
    x2 = float(elem.get('x2', 0))
    y2 = float(elem.get('y2', 0))
    pos1 = Vector([x1,y1]).en_matrix(matrix)
    pos2 = Vector([x2,y2]).en_matrix(matrix)

    if 'marker-end' in style and style['marker-end'] != 'none':
        direction = pos2-pos1
        attributes = {
                'color':color,
                'pos':(pos1+pos2)/2.0,
                'size':abs(pos1-pos2),
                'rotation':atan2(direction[1], direction[0]),
                }
        return LaserPen(attributes)
    elif 'marker-start' in style and style['marker-start'] != 'none':
        direction = pos2-pos1
        attributes = {
                'color':color,
                'pos':(pos1+pos2)/2.0,
                'size':abs(pos1-pos2),
                'rotation':atan2(direction[1], direction[0]),
                }
        return Thruster(attributes)
    else:
        attributes = {
                'color':color,
                'strengthFactor':0.25,
                'geom0pos':pos1,
                'geom1pos':pos2,
                }
        return Spring(attributes)

#}}}
def parse_polyline(elem, matrix, style): #{{{
    '''Comvert polyline into Plane'''
    color, drawBorder = style.getcolor_and_drawborder()

    points = elem.get('points', 0)
    match_=re.search(r'([^, ]*)[, ]*([^, ]*)[, ]*([^, ]*)[, ]*([^, ]*)[, ]*$', points)

    x0, y0 = float(match_.group(1)), float(match_.group(2))
    x1, y1 = float(match_.group(3)), float(match_.group(4))
    pos = Vector([x0,y0]).en_matrix(matrix)
    pos_end = Vector([x1,y1]).en_matrix(matrix)
    direction = pos_end - pos

    attributes = {
            'drawBorder':drawBorder,
            'color':color,
            'pos':pos,
            'angle':atan2(direction[1], direction[0]),
            }
    return Plane(attributes)
#}}}

# ========================================
def _parse_svg(phun_objects, element, inherited_matrix, inherited_style): #{{{
    for elem in list(element):
        current_style = SVG_Style(elem).inherit(inherited_style)
        current_matrix = inherited_matrix.combine(Transforms(elem.get('transform')).to_matrix())

        if   elem.tag == (XMLNS+'g'):
            _parse_svg(phun_objects, elem, current_matrix, current_style)
        elif elem.tag == (XMLNS+'defs'):
            _parse_svg(phun_objects, elem, current_matrix, current_style)
        elif elem.tag == (XMLNS+'clipPath'):
            warning(phun_objects)
            _parse_svg(phun_objects, elem, current_matrix, current_style)
        elif elem.tag == (XMLNS+'use'):
            e_ = elem.getAttributeNode("xlink:href") #FIXME
            warning(e_.childNodes) #FIXME

        elif elem.tag == (XMLNS+'path'):
            # NOTE: parse_path() returns list of objects,
            #        so, use 'extend' instead of 'append'.
            phun_objects.extend(parse_path(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'rect'):
            phun_objects.append(parse_rect(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'circle'):
            phun_objects.append(parse_circle(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'ellipse'):
            phun_objects.append(parse_ellipse(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'text'):
            pass #TODO deal text element
            #phun_objects.append(parse_text(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'polyline'):
            phun_objects.append(parse_polyline(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'line'):
            phun_objects.append(parse_line(elem, current_matrix, current_style))
        elif elem.tag == (XMLNS+'polygon'):
            phun_objects.append(parse_polygon(elem, current_matrix, current_style))

def parse_svg(phun_objects, element, #{{{
              matrix=Matrix([1,0,0,1,0,0]),
              style=SVG_Style({'fill'          :'black', 
                               'fill-opacity'  :'1',
                               'stroke'        :'none',
                               'stroke-opacity':'1',
                               'opacity'       :'1'      })):
    _parse_svg(phun_objects, element, matrix, style)
    for (i, o) in enumerate(phun_objects):
        if isinstance(o, _PhunGeometry):
            o['geomID'] = i+1
    for (i, o) in enumerate(phun_objects):
        if isinstance(o, _PhunAttachment):
            if not o.try_attatch(phun_objects):
                del phun_objects[i]
#}}}
# ========================================
if __name__ == '__main__': #{{{
    f = open(sys.argv[1], 'r')
    et = ElementTree(file=f)
    f.close()
    scaleX, scaleY = 1/90.0, -1/90.0 # Inkscape's 1 inch -> Algodoo's 1 meter
    #scaleX, scaleY = 1,1
    transform = Transforms("scale(%lf,%lf)" % (scaleX, scaleY))
    phun_objects = []
    parse_svg(phun_objects, et.getroot(), matrix=transform.to_matrix())

    # Print comverted data
    print ("// Phun scene created by %s v%s" % (sys.argv[0], __version__))
    
    # Print geometries
    for o in phun_objects:
        if isinstance(o, _PhunGeometry):
            print (str(o))

    # Print attachments
    for o in phun_objects:
        if isinstance(o, _PhunAttachment):
            print (str(o))

    if ORIGINAL_SVG_DATA_OUTPUT:
        # Print original data
        print ('/** Original SVG data')
        f = open(sys.argv[1], 'r')
        for line in f:
            print (line[:-1])
        f.close()
        print ('*/')
#}}}

# vim: foldmethod=marker expandtab shiftwidth=4 tabstop=8 softtabstop=4 fileencoding=utf-8 textwidth=99
