#!/usr/bin/env python
# vim: fileencoding=utf-8

"""
Copyright (C) 2011 Tatt61880 (tatt61880@gmail.com, @tatt61880)
Last Modified: 2012/04/21 18:00:26.

"""

from optparse import OptionParser, OptionValueError
import sys
import unittest
import phn_output
from xml.etree.ElementTree import fromstring
from math import *

parser = OptionParser()
parser.add_option(
    "-d", "--debug",
     action="store_true", # Trueを保存
                          # store_falseならFalseを保存
     default=False,
     help="debug"
)
parser.add_option(
    "-X", "--disable_warnings",
     action="store_true",
     default=False,
     help="disable_warnings"
)
(options, args) = parser.parse_args()

if options.disable_warnings:
    phn_output.warning = lambda x: x


# ============================================
def create_elements(e):#{{{
    ret = ""
    if isinstance(e, tuple):
        ret += "<g "
        for key, value in e[0].items():
            ret += ''' %s="%s"''' % (key, value)
        ret += "> "
        ret += create_elements(e[1])
        ret += "</g>"
    elif isinstance(e, list):
        for e_ in e:
            ret += create_elements(e_)
    else:
        ret += "<%s " % e.pop('tag')
        for key, value in e.items():
            ret += ''' %s="%s"''' % (key, value)
        ret += " />"
    return ret
#}}}
def parse_elements(elements):#{{{
    elements_data = create_elements(elements)

    svg_data = fromstring("""
<svg
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   width="90"
   height="90"
   id="svg2"
   version="1.1"
   inkscape:version="0.48.0 r9654"
   sodipodi:docname="a.svg">""" + elements_data + "</svg>")
    phunData=[]
    phn_output.parse_svg(phunData, svg_data)
    return phunData
#}}}

# ============================================
# Classes
# ============================================
class Vecs(list): #{{{
    def __init__(self, vecs):
        self.extend([phn_output.Vector(a) for a in vecs])
#}}}

class _SVG_element(dict):#{{{
    default_attributes = None
    def parse(self):
        return parse_elements(self)[0]
    def __init__(self, **keywords):
        self.update(self.default_attributes)
        self.update(**keywords)
#}}}
class Path(_SVG_element):#{{{
    default_attributes = dict(tag='path', d='M 0,0 1,0 0,1z')
#}}}
class Rect(_SVG_element):#{{{
    default_attributes = dict(tag='rect', width=1, height=1)
#}}}
class Circle(_SVG_element):#{{{
    default_attributes = dict(tag='circle', r=1)
#}}}
class PathCircleRadius1m(_SVG_element):#{{{  #FIXME Inkscapeからの依存をなくす
    default_attributes = {
            'tag':'path',
            'sodipodi:cx':0, 'sodipodi:cy':0, 'sodipodi:rx':1, 'sodipodi:ry':1, 'sodipodi:type':'arc',
            'd':'m -1,-1 a 1,1 0 0 0 1,0 1,1 0 0 0 -1,0 z'
            }
#}}}
class Ellipse(_SVG_element):#{{{
    default_attributes = dict(tag='ellipse', cx=0, cy=0)
#}}}

class Line(_SVG_element):#{{{
    default_attributes = dict(tag='line', x1=0, y1=0, x2=0, y2=0)
#}}}
class Polyline(_SVG_element):#{{{
    default_attributes = dict(tag='polyline')
#}}}
class Polygon(_SVG_element):#{{{
    default_attributes = dict(tag='polygon')
#}}}

# ============================================
# Tests
# ============================================
# Geoms
class testPath(unittest.TestCase):#{{{
    pass #TODO Pathが真円状の場合に, sodipodi:rxのような表記がなくても、Polygonでなく、Circleに変換できるように。
#    def test_path_perfect_circle(self):
#        p = Path(d="m -201.59999,10.8 a 28.799999,28.799999 0 1 1 -57.6,0 28.799999,28.799999 0 1 1 57.6,0 z").parse()
#        self.assertTrue(isinstance(p, phn_output.Circle))

    def test_path_pos(self):#{{{2
        p = Path(d="M0 0 10 0 10 10 0 10").parse()
        self.assertAlmostEqual(p['pos'], phn_output.Vector([5, 5]))
    #}}}2
    def test_path_area(self):#{{{2
        p = Path(d="M0 0 10 0 10 10 0 10").parse()
        self.assertAlmostEqual(p._area, 100)
    #}}}2
    def test_path_pos_triangle(self):#{{{2
        p = Path(d="M0 0 10 0 5 6").parse()
        self.assertAlmostEqual(p['pos'], phn_output.Vector([5, 2]))
    #}}}2
    def test_path_laststring_equals_whitespace(self):#{{{2
        p = Path(d="M0 0 10 0 5 6 ").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
    #}}}2
    def test_path_pos_hollow(self):#{{{2
        p = Path(d="M0 0 10 0 10 10 0 10zM1 1 6,1 6,6 1 6z").parse()
        self.assertAlmostEqual(p['pos'], phn_output.Vector([5.5, 5.5]))
    #}}}2
    def test_path_pos_hollow2(self):#{{{2
        p = Path(d="M0 0 10 0 10 10 0 10zM1 1 1,6 6,6 6 1z").parse()
        self.assertAlmostEqual(p['pos'], phn_output.Vector([5.5, 5.5]))
    #}}}2
    def test_path_pos_hollow_noncommand_followingZ(self):#{{{2
        # z以下が無視される
        p = Path(d="M0 0 10 0 10 10 0 10z1 1 6,1 6,6 1 6z").parse()
        self.assertAlmostEqual(p['pos'], phn_output.Vector([5.0, 5.0]))
    #}}}2
    def test_path_arc_ellipse(self):#{{{2
        p = Path(d="m 95.400003,53.099998 a 8.1000004,15.3 0 1 1 -16.2,0 a 8.1000004,15.3 0 1 1 16.2,0 z").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
    #}}}2
    def test_path_h_v(self):#{{{2
        p = Path(d="M 14 13 h 60 v 60").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
        self.assertAlmostEqual(p['pos'], phn_output.Vector([54.0, 33.0]))
    #}}}2
    def test_path_H_V(self):#{{{2
        p = Path(d="M 20 30 H 50 V 60").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
        self.assertAlmostEqual(p['pos'], phn_output.Vector([40.0, 40.0]))
    #}}}2
    def test_path_q(self):#{{{2
        p = Path(d="m 214.28571,452.36218 q 0,0 -239.99999,-692.36218 q -239.99999,-692.36218 357.14286,-74.28571z").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
    #}}}2
    def test_path_Q(self):#{{{2
        p = Path(d="m 214.28571,452.36218 Q 928.57143,303.79076 417.14286,-100 z").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
    #}}}2
#}}}
class testRect(unittest.TestCase):#{{{
    def test_rect(self): #{{{2
        p = Rect(width=100,height=30).parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["size"], tuple([100, 30]))
    #}}}2
    def test_rect_rotate90deg(self):
        p = Rect(transform="rotate(90)").parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["angle"], pi/2)

    def test_rect_rotate30deg(self):
        p = Rect(transform="rotate(30)").parse()
        self.assertAlmostEqual(p['angle'], pi/6)

    def test_rect_rotate0deg(self):
        p = Rect(transform="rotate(0)").parse()
        self.assertEqual(p["angle"], 0)

    def test_rect_rotate3args(self):
        p = Rect(transform="rotate(30 100 200)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertAlmostEqual(p['angle'], pi/6)

    def test_rect_double_transform(self):
        p = Rect(transform="rotate(0) rotate(60)").parse()
        self.assertAlmostEqual(p["angle"], pi/3)

    def test_rect_double_transform2(self):
        p = Rect(width=100, height=200, transform="rotate(30) scale(10, 3)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertAlmostEqual(p['angle'], pi/6)
        self.assertEqual(p["size"], (1000,600))

    def test_rect_matrix(self):
        p = Rect(width=100, height=200, transform="matrix(2,0,0,1,0,0)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["angle"], 0)
        self.assertEqual(p["size"], (200,200))

    def test_rect_sclae(self):
        p = Rect(width=100, height=200, transform="scale(2, -1)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["size"], (200,200))

    def test_rect_void_transform(self):
        p = Rect().parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["angle"], 0)

    def test_rect_transform2polygon(self):
        p = Rect(transform="scale(10, 2) rotate(30)").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))

    def test_rect_ry(self):
        p = Rect(ry="0.1").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))

    def test_rect_ry_rx0(self):
        p = Rect(ry="0.1", rx="0").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
#}}}
class testCircle(unittest.TestCase): #{{{
    def test_circle(self):
        p = Circle(r=1).parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Circle))
        self.assertEqual(p["radius"], 1)

    def test_circle_scale(self):
        p = Circle(r=1, transform="scale(2,1)").parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Polygon))

    def test_circle_filtered(self):
        '''Filtered circle should be converted into tracer'''
        p = Circle(r=1, style="filter:hoge").parse()
        self.assertTrue(isinstance(p, phn_output._PhunAttachment))
        self.assertTrue(isinstance(p, phn_output.Pen))

#}}}
class testInkscapeEllipse(unittest.TestCase):#{{{
    def test_inkscape_ellipse_normal_ellipse(self):
        p = PathCircleRadius1m().parse()
        self.assertTrue(isinstance(p, phn_output.Circle))

    def test_inkscape_ellipse_rotated_ellipse(self):
        p = PathCircleRadius1m(transform="rotate(30)").parse()
        self.assertTrue(isinstance(p, phn_output.Circle), type(p))
        self.assertTrue('angle' in p)
        self.assertAlmostEqual(p['angle'], pi/6)
        self.assertEqual(p['radius'], 1)

    def test_inkscape_ellipse_scaled_ellipse(self):
        p = PathCircleRadius1m(transform="scale(1,2)").parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))

    def test_inkscape_ellipse_ellipse_with_end_angle(self):
        p = PathCircleRadius1m(**{"sodipodi:end":"1"}).parse()
        self.assertTrue(isinstance(p, phn_output.Polygon))
#}}}
class testEllipse(unittest.TestCase): #{{{
    def test_ellipse(self):
        p = Ellipse(rx=2, ry=1).parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Polygon))

    def test_ellipse_rx_equal_ry(self):
        p = Ellipse(rx=2, ry=2).parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Circle))
        self.assertTrue(p['radius'], 2)

    def test_ellipse_rx_equal_ry_scaled(self):
        p = Ellipse(rx=2, ry=2, transform="scale(1,2)").parse()
        self.assertTrue(isinstance(p, phn_output._PhunGeometry))
        self.assertTrue(isinstance(p, phn_output.Polygon))

#}}}
# ============================================
class testSpringGeom0Geom1(unittest.TestCase): #{{{1
    """
    For testing attachment issue.
    Thanks nishina2525 for reporting this issue!
    http://nishina2525.cocolog-nifty.com/blog/2012/04/phn-3a3b.html
    """
    def test_1_2_case1(self):
        elements = [Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 1);
        self.assertEqual(p['geom1'], 2);

    def test_1_2_case2(self):
        elements = [Rect(**{"x": -1,  "y":-1, "height":2, "width":200}),
                    Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 1);
        self.assertEqual(p['geom1'], 2);

    def test_2_1_case1(self):
        elements = [Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 2);
        self.assertEqual(p['geom1'], 1);

    def test_2_1_case2(self):
        elements = [Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x": -1,  "y":-1, "height":2, "width":200}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 2);
        self.assertEqual(p['geom1'], 1);

    def test_none_none_case1(self):
        elements = [Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        objects = parse_elements(elements)
        self.assertEqual(len(objects), 2); # No Spring

    def test_none_none_case2(self):
        elements = [Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        objects = parse_elements(elements)
        self.assertEqual(len(objects), 1); # No Spring

    def test_none_none_case3(self):
        elements = [Path(**{"d":"m 0,0 10,0"}),]
        objects = parse_elements(elements)
        self.assertEqual(len(objects), 0); # No Spring

    def test_none_none_case4(self):
        elements = [Path(**{"d":"m 0,0 10,0"}),
                    Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    ]
        objects = parse_elements(elements)
        self.assertEqual(len(objects), 2); # No Spring

    def test_1_none_case1(self):
        elements = [Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 1);
        self.assertEqual(p['geom1'], 0);

    def test_1_none_case2(self):
        elements = [Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[1] # spring
        self.assertEqual(p['geom0'], 1);
        self.assertEqual(p['geom1'], 0);

    def test_1_none_case3(self):
        elements = [Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),
                    Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),]
        p = parse_elements(elements)[1] # spring
        self.assertEqual(p['geom0'], 1);
        self.assertEqual(p['geom1'], 0);

    def test_2_none_case1(self):
        elements = [Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x": -1,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 2);
        self.assertEqual(p['geom1'], 0);

    def test_none_1_case1(self):
        elements = [Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 0);
        self.assertEqual(p['geom1'], 1);

    def test_none_2_case1(self):
        elements = [Rect(**{"x":100,  "y":-1, "height":2, "width":2}),
                    Rect(**{"x":  9,  "y":-1, "height":2, "width":2}),
                    Path(**{"d":"m 0,0 10,0"}),]
        p = parse_elements(elements)[2] # spring
        self.assertEqual(p['geom0'], 0);
        self.assertEqual(p['geom1'], 2);


#}}}1

class testGroup(unittest.TestCase):#{{{
    def test_group_rotates(self):
        elements = ({"transform":"rotate(30)"}, 
                        Rect(**{"transform":"rotate(60)"}))
        p = parse_elements(elements)
        self.assertAlmostEqual(p[0]['angle'], pi/2)
        self.assertTrue(isinstance(p[0], phn_output.Box))

    def test_group_scales(self):
        elements = ({"transform":"scale(1,-3)"},
                        Rect(**{"width":100, "height":100, "transform":"scale(10,2)"}))
        p = parse_elements(elements)
        self.assertEqual(p[0]['size'], phn_output.Vector([1000, 600]))

    def test_group_scales_triple(self):
        elements = ({"transform":"scale(0.5,-3)"},
                        ({"transform":"scale(1,-3)"},
                            Rect(**{"width":100, "height":100, "transform":"scale(10,2)"})))
        p = parse_elements(elements)[0]
        self.assertEqual(p['size'], phn_output.Vector([500, 1800]))

    def test_group_opacity(self):
        elements = ({"style":"opacity:0.2"},
                        ({"opacity":"0.3"},
                            Rect(**{"style":"fill-opacity:0.7;fill:#00FFFF"})))
        p = parse_elements(elements)[0]
        self.assertAlmostEqual(p['color'][3], 0.042)

    def test_group_inherited_color(self):
        elements = ({"style":"fill:red"},
                        Rect(**{"style":""}))
        p = parse_elements(elements)[0]
        self.assertEqual(p['color'], phn_output.Color([1,0,0,1]))

#}}}
# ============================================
class testStyle(unittest.TestCase): #{{{
    def test_style_fill_red(self):
        p = Rect(style='fill:#FF0000').parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 0, 1]))

    def test_style_fill_red2(self):
        p = Rect(style='fill:#F00').parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 0, 1]))

    def test_style_fill_red3(self):
        p = Rect(style='fill:rgb(100%,0,0)').parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 0, 1]))

    def test_style_fill_red4(self):
        p = Rect(style='fill:rgb(255,0,0)').parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 0, 1]))

    def test_style_fill_010101(self):
        p = Rect(style="fill:#0180B9").parse()
        self.assertEqual(p["color"], phn_output.Color([1/255., 0x80/255., 1.0*0xB9/0xFF, 1.0]))

    def test_style_fill_lowercase(self):
        p = Rect(style="fill:#ff00ff").parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 1, 1]))

    def test_style_notGiven(self):
        p = Rect(style="").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 1]))

    def test_style_none(self):
        p = Rect(style="fill:none").parse()
        self.assertEqual(p["color"][3], 0)

    def test_style_fill_none_strokeFF00FF(self):
        p = Rect(style="fill:none;stroke:#FF00FF").parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 1, 0]))

    def test_style_invalid(self):
        p = Rect(style="a").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 1]))

    def test_style_invalid2(self):
        p = Rect(style="a; fill:#00FF00").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 1]))

    def test_style_invalid3(self):
        p = Rect(style="fill:blackk").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 1]))

    def test_style_invalid4(self):
        p = Rect(style="fill:rgb(1,2,3,4)").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 1]))

    def test_style_fill_opacity(self):
        p = Rect(style="fill:#FF0000; opacity:0.5").parse()
        self.assertEqual(p["color"], phn_output.Color([1, 0, 0, 0.5]))

    def test_style_fill_string(self):
        p = Rect(style="fill:blue;").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 1, 1]))

    def test_style_fill_none_stroke_none(self):
        p = Rect(style="fill:none; stroke:none").parse()
        self.assertEqual(p["color"], phn_output.Color([0, 0, 0, 0]))
#}}}
# ============================================
class testMatrix(unittest.TestCase): #{{{
    def test_matrix(self):
        p = Rect(width=100, height=200, transform="scale(2, -1)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["size"], (200,200))

    def test_matrix_invalid(self):
        p = Rect(width=100, height=200, transform="scale(2, -1").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["size"], (100,200))

    def test_matrix_invalid2(self):
        p = Rect(width=100, height=200, transform="scale(2, -1, 3)").parse()
        self.assertTrue(isinstance(p, phn_output.Box))
        self.assertEqual(p["size"], (100,200))
#}}}
class testVector(unittest.TestCase):#{{{
    def test_vector_add(self):
        a = phn_output.Vector([1,2])
        b = phn_output.Vector([3,4])
        self.assertEqual(a+b, phn_output.Vector([4, 6]))

    def test_vector_pos(self):
        a = phn_output.Vector([1,2])
        self.assertEqual(+a, phn_output.Vector([1, 2]))

    def test_vector_neg(self):
        a = phn_output.Vector([1,2])
        self.assertEqual(-a, phn_output.Vector([-1, -2]))

    def test_vector_norm(self):
        a = phn_output.Vector([3,4])
        self.assertEqual(abs(a), 5)
#}}}
# ============================================

def check_vecs(self, original, expected, received):#{{{1
    self.assertEqual(len(expected), len(received))
    for a, b in zip(expected, received):
        self.assertTrue(a[0] == b[0] and a[1] == b[1],
                "\nvecs:    " + str(original)+ "\nExpected:" + repr(expected) + "\nReceived:" +
                repr(received))
#}}}1
def check_surfaces(self, original, expected_surfaces, received_surfaces): #{{{1
    self.assertEqual(len(expected_surfaces), len(received_surfaces),
            "\nOriginal:    " + str(original)+ "\nExpected:" + repr(expected_surfaces) + "\nReceived:" + repr(received_surfaces))
    for i, (expected_vecs, my_answer_vecs) in enumerate(zip(expected_surfaces, received_surfaces)):
        self.assertEqual(len(expected_vecs), len(my_answer_vecs),
                "\nOriginal:    " + str(original)+ "\nExpected[" + str(i) + "]:" + repr(expected_vecs) + "\nReceived[" + str(i) + "]:" + repr(my_answer_vecs))
        for a, b in zip(expected_vecs, my_answer_vecs):
            self.assertTrue(a[0] == b[0] and a[1] == b[1],
                    "\nOriginal:    " + str(original)+ "\nExpected:" + repr(expected_surfaces) + "\nReceived:" + repr(received_surfaces))
#}}}1

# Self-intersection solver
class testSimple(unittest.TestCase): #{{{1
    def test_box(self): #{{{2
        vecs = Vecs([[0,0], [2,0], [2,2], [0,2], [0,0]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = vecs
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_box2(self): #{{{2
        vecs = Vecs([[0,0], [2,0], [2,2], [0,2]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = vecs
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_box3(self): #{{{2
        vecs = Vecs([[0,0], [0,2], [2,2], [2,0]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = vecs
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_triangle(self): #{{{2
        vecs = Vecs([[0,0], [0,2], [2,2]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = vecs
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
#}}}1
class testCross(unittest.TestCase): #{{{
    def test_cross1(self): #{{{2
        vecs = Vecs([[0,0], [2,0], [1,1], [1,-1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [1, 0], [1, 1], [2, 0], [1, 0], [1, -1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_cross2(self):#{{{2
        vecs = Vecs([[0,0], [2,0], [1,1], [1,0], [1,-1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [1, 0], [1, 1], [2, 0], [1, 0], [1, -1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_cross3(self): #{{{2
        vecs = Vecs([[0,0], [1,0], [2,0], [1,1], [1,-1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [1, 0], [1, 1], [2, 0], [1, 0], [1, -1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_cross4(self): #{{{2
        vecs = Vecs([[0,0], [1,0], [2,0], [1,1], [1,0], [1,-1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [1, 0], [1, 1], [2, 0], [1, 0], [1, -1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_non_cross(self): #{{{2
        vecs = Vecs([[0,0], [2,0], [1,1], [1,0], [0,1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [2, 0], [1, 1], [1, 0], [0, 1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_non_cross2(self): #{{{2
        vecs = Vecs([[0,0], [2,0], [1,1], [1,0], [0,1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [2, 0], [1, 1], [1, 0], [0, 1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
#}}}
class testDoubleCross(unittest.TestCase): #{{{1
    def test_double_cross1(self): #{{{2
        vecs = Vecs([[0,0], [0,2], [2,0], [2,1], [-1,1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [0, 1], [1, 1], [2, 0], [2, 1], [1, 1], [0, 2], [0, 1], [-1, 1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
#}}}1
class testTripleCross(unittest.TestCase): #{{{1
    def test_triplecross1(self): #{{{2
        vecs = Vecs([[0,0], [0,2], [2,0], [2,2], [3,1], [-1,1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [0, 1], [1, 1], [2, 0], [2, 1], [3, 1], [2, 2], [2, 1], [1, 1] , [0, 2], [0, 1], [-1, 1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
    def test_triplecross2(self): #{{{2
        vecs = Vecs([[0,0], [0,2], [2,0], [2,4], [-2,1], [3,1]])
        my_answer = phn_output.solve_self_intersection(vecs)
        expected = [[0, 0], [0, 1], [-2, 1], [2, 4], [2, 1], [1, 1], [0, 2], [0, 1], [1, 1], [2, 0], [2, 1], [3, 1]]
        check_vecs(self, vecs, expected, my_answer)
    #}}}2
#}}}1

def rectangle_path(xmin=0, ymin=0, width=None, height=None, xmax=None, ymax=None):
    if width  != None: xmax = xmin + width
    if height != None: ymax = ymin + height
    return "M%d %d %d %d %d %d %d %dz" % (xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax)

def rectangle_vecs(xmin=0, ymin=0, width=None, height=None, xmax=None, ymax=None):
    if width  != None: xmax = xmin + width
    if height != None: ymax = ymin + height
    return [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]

class testCompoundPaths(unittest.TestCase): #{{{
    def test_compoind_path_hollow(self): #{{{2
        path = rectangle_path(xmin=0, ymin=0, width=10, height=10) + rectangle_path(xmin=1, ymin=1, width=8, height=8)
        p = Path(d=path).parse()
        expected = [rectangle_vecs(xmin=0, ymin=0, width=10, height=10), rectangle_vecs(xmin=1, ymin=1, width=8, height=8)]
        received_surfaces = p['surfaces']
        check_surfaces(self, path, expected, p['surfaces'])
    #}}}2
    def test_compoind_path_hollow2(self): #{{{2
        path = "M0,0 3,0 3,2 4,1 4,3 0,3z"  + rectangle_path(xmin=1, ymin=1, width=1, height=1)
        p = Path(d=path).parse()
        expected = [[[0,0], [3,0], [3,2], [4,1], [4,3], [0,3], [0,0]], rectangle_vecs(xmin=1, ymin=1, width=1, height=1)]
        received_surfaces = p['surfaces']
        check_surfaces(self, path, expected, p['surfaces'])
    #}}}2
#    def test_compoind_path_compound1(self): #{{{2
#        path = "M0 0 2 0 2 2 0 2z M1 1 3 1 3 3 1 3"
#        phun_objects = parse_elements(Path(d=path))
#        expected = [[[0,0]]] #FIXME
#
#        self.assertEqual(len(phun_objects), 1)
#        check_surfaces(self, path, expected, phun_objects[0]['surfaces'])
#    #}}}2
    def test_compoind_path_2objects(self): #{{{2
        path = "M0 0 10 0 10 10 0 10z M11 0 21 0 21 10 11 10"
        phun_objects = parse_elements(Path(d=path))
        expected0 = [[[0,0], [10,0], [10,10], [0,10], [0, 0]]]
        expected1 = [[[11,0], [21,0], [21,10], [11,10], [11,0]]]

        check_surfaces(self, path, expected0, phun_objects[0]['surfaces'])
        check_surfaces(self, path, expected1, phun_objects[1]['surfaces'])
    #}}}2
#}}}
class testIsInclude(unittest.TestCase): #{{{1
    def test_include1(self): #{{{2
        vecs = phn_output.Vecs(rectangle_vecs(xmin=0, ymin=0, width=2, height=2))
        self.assertTrue(vecs.is_include([1,1]), vecs)
        self.assertTrue(vecs.is_include([2,2], include_on_edge=True), vecs)
        self.assertFalse(vecs.is_include([2,2], include_on_edge=False), vecs)
        self.assertFalse(vecs.is_include([3,3], include_on_edge=False), vecs)
    #}}}2
    def test_include2(self): #{{{2
        vecs = phn_output.Vecs([[0,0], [2,2], [4,0], [4,4], [0,4]])
        self.assertTrue(vecs.is_include([1,3]), vecs)
        self.assertTrue(vecs.is_include([1,2]), vecs)
        self.assertTrue(vecs.is_include([1,1], include_on_edge=True), vecs)
        self.assertFalse(vecs.is_include([1,1], include_on_edge=False), vecs)
        self.assertFalse(vecs.is_include([1,0]), vecs)
    #}}}2
    def test_include3(self): #{{{2
        vecs = phn_output.Vecs([[0,0], [4,0], [4,4], [2,2], [0,4]])
        self.assertFalse(vecs.is_include([1,4]), vecs)
        self.assertFalse(vecs.is_include([1,3], include_on_edge=False), vecs)
        self.assertTrue(vecs.is_include([1,3], include_on_edge=True), vecs)
        self.assertTrue(vecs.is_include([1,2]), vecs)
        self.assertTrue(vecs.is_include([1,1]), vecs)
    #}}}2
#}}}1
class testComplexCompoundPaths(unittest.TestCase): #{{{1
    #path0 = rectangle_path(xmin=-1, ymin=-1, width=7, height=7)
    path1 = rectangle_path(xmin=0, ymin=0, width=5, height=5)
    path2 = rectangle_path(xmin=1, ymin=1, width=3, height=3)
    path3 = rectangle_path(xmin=2, ymin=2, width=1, height=1)
    path4 = rectangle_path(xmin=1, ymin=1, width=1, height=1)
    path5 = rectangle_path(xmin=3, ymin=1, width=1, height=1)
    expected0 = [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]], [[1, 1], [4, 1], [4, 4], [1, 4], [1, 1]]]
    expected1 = [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
    expected2 = [rectangle_vecs(xmin=0, ymin=0, width=5, height=5), rectangle_vecs(xmin=1, ymin=1,
        width=1, height=1), rectangle_vecs(xmin=3, ymin=1, width=1, height=1)]

    def check_triplet(self, path):
        phun_objects = parse_elements(Path(d=path))
        check_surfaces(self, path, self.expected0, phun_objects[0]['surfaces'])
        self.assertTrue(len(phun_objects) != 1, len(phun_objects))
        check_surfaces(self, path, self.expected1, phun_objects[1]['surfaces'])
        self.assertEqual(len(phun_objects), 2, "Wasteful surfaces:" + repr(phun_objects[-1]['surfaces']))

    def test_compoind_path_triplet1(self): #{{{2
        self.check_triplet(self.path1 + self.path2 + self.path3)
    #}}}2
    def test_compoind_path_triplet2(self): #{{{2
        self.check_triplet(self.path1 + self.path3 + self.path2)
    #}}}2
    def test_compoind_path_triplet3(self): #{{{2
        self.check_triplet(self.path2 + self.path3 + self.path1)
    #}}}2
    def test_compoind_path_triplet4(self): #{{{2
        self.check_triplet(self.path2 + self.path1 + self.path3)
    #}}}2
    def test_compoind_path_triplet5(self): #{{{2
        self.check_triplet(self.path3 + self.path1 + self.path2)
    #}}}2
    def test_compoind_path_triplet6(self): #{{{2
        self.check_triplet(self.path3 + self.path2 + self.path1)
    #}}}2
    def test_compoind_path_triplet7(self): #{{{2
        path = self.path1 + self.path4 + self.path5
        phun_objects = parse_elements(Path(d=path))
        check_surfaces(self, path, self.expected2, phun_objects[0]['surfaces'])
        self.assertEqual(len(phun_objects), 1)
    #}}}2
    def test_compoind_path_triplet8(self): #{{{2
        path = self.path4 + self.path5 + self.path1
        phun_objects = parse_elements(Path(d=path))
        check_surfaces(self, path, self.expected2, phun_objects[0]['surfaces'])
        self.assertEqual(len(phun_objects), 1)
    #}}}2
#}}}1

# ============================================

class testSVG_Path(unittest.TestCase): #{{{1
    def checkSVG(self, _path, _ans):
        str_path = str(_path)
        str_ans = str(_ans)
        self.assertEqual(str_path, str_ans, "\n       path = " + str_path + "\nIt should be: " + str_ans)
        
    def test_M_withImplicitL(self):
        path = phn_output.SVG_Path("M 0 5 10 20 30 40")
        ans = [['M', [0, 5]], ['L', [10, 20]], ['L', [30, 40]]]
        self.checkSVG(path, ans)
        
    def test_Z(self):
        path = phn_output.SVG_Path("M 0 5 10 20 z")
        ans = [['M', [0, 5]], ['L', [10, 20]], ['L', [0, 5]]]
        self.checkSVG(path, ans)

    def test_minus(self):
        path = phn_output.SVG_Path("M-1-2-3-4z")
        ans = [['M', [-1, -2]], ['L', [-3, -4]], ['L', [-1, -2]]]
        self.checkSVG(path, ans)

    def test_incorrectPath(self):
        path = phn_output.SVG_Path("Mu-0-5-10-20z")
        ans = []
        self.checkSVG(path, ans)

    def test_incorrectPath2(self):
        path = phn_output.SVG_Path("L-0-5-10-20z")
        ans = []
        self.checkSVG(path, ans)


#}}}1


class testDebug(unittest.TestCase): #{{{1
     def test_rect_ry(self):
        p = Rect(ry="0.1").parse()
        #print type(p)
        self.assertTrue(isinstance(p, phn_output.Polygon))

#}}}1

##############################################
def suite(): #{{{
    suite = unittest.TestSuite()

    DEBUG = options.debug
    if DEBUG:
        suite.addTest(unittest.makeSuite(testDebug))
    else:
        suite.addTest(unittest.makeSuite(testPath))
        suite.addTest(unittest.makeSuite(testRect))
        suite.addTest(unittest.makeSuite(testCircle))
        suite.addTest(unittest.makeSuite(testInkscapeEllipse))
        suite.addTest(unittest.makeSuite(testEllipse))

        suite.addTest(unittest.makeSuite(testSpringGeom0Geom1))

        suite.addTest(unittest.makeSuite(testGroup))

        suite.addTest(unittest.makeSuite(testStyle))

        suite.addTest(unittest.makeSuite(testMatrix))
        suite.addTest(unittest.makeSuite(testVector))

        suite.addTest(unittest.makeSuite(testSimple))
        suite.addTest(unittest.makeSuite(testCross))
        suite.addTest(unittest.makeSuite(testDoubleCross))
        suite.addTest(unittest.makeSuite(testTripleCross))
        suite.addTest(unittest.makeSuite(testCompoundPaths))
        suite.addTest(unittest.makeSuite(testComplexCompoundPaths))

        suite.addTest(unittest.makeSuite(testIsInclude))

        suite.addTest(unittest.makeSuite(testSVG_Path))
    return suite
#}}}

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=1).run(suite())

# vim: foldmethod=marker expandtab shiftwidth=4 tabstop=8 softtabstop=4 fileencoding=utf-8 textwidth=99
