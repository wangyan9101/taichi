import sys
import os
import datetime
import platform
import random
import taichi


def get_os_name():
    name = platform.platform()
    if name.lower().startswith('darwin'):
        return 'osx'
    elif name.lower().startswith('windows'):
        return 'win'
    elif name.lower().startswith('linux'):
        return 'linux'
    assert False, "Unknown platform name %s" % name


def get_uuid():
    print 'Warning: get_uuid is deprecated. Please use get_unique_task_id instead.'
    return get_unique_task_id()


def get_unique_task_id():
    return datetime.datetime.now().strftime('task-%Y-%m-%d-%H-%M-%S-r') + ('%05d' % random.randint(0, 10000))


import copy
import numpy as np
import ctypes


def config_from_dict(args):
    from taichi.core import tc_core
    from taichi.visual import SurfaceMaterial
    d = copy.deepcopy(args)
    for k in d:
        if isinstance(d[k], SurfaceMaterial):
            d[k] = d[k].id
        d[k] = str(d[k])
    return tc_core.config_from_dict(d)


def make_polygon(points, scale):
    import taichi as tc
    polygon = tc.core.Vector2List()
    for p in points:
        if type(p) == list or type(p) == tuple:
            polygon.append(scale * Vector(p[0], p[1]))
        else:
            polygon.append(scale * p)
    return polygon


def Vectori(*args):
    from taichi.core import tc_core
    if isinstance(args[0], tc_core.Vector2i):
        return args[0]
    if isinstance(args[0], tc_core.Vector3i):
        return args[0]
    if isinstance(args[0], tuple):
        args = tuple(*args)
    if len(args) == 2:
        return tc_core.Vector2i(int(args[0]), int(args[1]))
    elif len(args) == 3:
        return tc_core.Vector3i(int(args[0]), int(args[1]), int(args[2]))
    else:
        assert False, type(args[0])


def Vector(*args):
    from taichi.core import tc_core
    if isinstance(args[0], tc_core.Vector2):
        return args[0]
    if isinstance(args[0], tc_core.Vector3):
        return args[0]
    if isinstance(args[0], tc_core.Vector4):
        return args[0]
    if isinstance(args[0], tuple):
        args = tuple(*args)
    if len(args) == 2:
        return tc_core.Vector2(float(args[0]), float(args[1]))
    elif len(args) == 3:
        return tc_core.Vector3(float(args[0]), float(args[1]), float(args[2]))
    elif len(args) == 4:
        return tc_core.Vector4(float(args[0]), float(args[1]), float(args[2]), float(args[3]))
    else:
        assert False, type(args[0])


def default_const_or_evaluate(f, default, u, v):
    if f == None:
        return default
    if type(f) in [float, int, tuple]:
        return f
    return f(u, v)


def const_or_evaluate(f, u, v):
    import taichi as tc
    if type(f) in [float, int, tuple, tc.core.Vector2, tc.core.Vector3]:
        return f
    return f(u, v)


# color_255: actual color
# arr: the transparance of the image, if transform is not 'levelset'
# transform: (x0, x1) as rescaling or simply 'levelset'
def array2d_to_image(arr, width, height, color_255=None, transform='levelset', alpha_scale=1.0):
    from taichi import tc_core
    if color_255 is None:
        assert isinstance(arr, tc_core.Array2DVector3) or isinstance(arr, tc_core.Array2DVector4)
    import pyglet
    rasterized = arr.rasterize(width, height)
    raw_data = np.empty((width, height, arr.get_channels()), dtype=np.float32)
    rasterized.to_ndarray(raw_data.ctypes.data_as(ctypes.c_void_p).value)
    if transform == 'levelset':
        raw_data = (raw_data <= 0).astype(np.float32)
    else:
        x0, x1 = transform
        raw_data = (np.clip(raw_data, x0, x1) - x0) / (x1 - x0)
    raw_data = raw_data.swapaxes(0, 1).copy()
    if isinstance(arr, tc_core.Array2DVector3):
        dat = np.stack([raw_data, np.ones(shape=(width, height, 1), dtype=np.float32)], axis=2).flatten().reshape(
            (height * width, 4))
        dat = dat * 255.0
    elif isinstance(arr, tc_core.Array2DVector4):
        dat = raw_data.flatten().reshape((height * width, 4))
        dat = dat * 255.0
    else:
        raw_data = raw_data.flatten()
        dat = np.outer(np.ones_like(raw_data), color_255)
        dat[:, 3] = (color_255[3] * raw_data)
    dat[:, 3] *= alpha_scale
    dat = np.clip(dat, 0.0, 255.0)
    dat = dat.astype(np.uint8)
    assert dat.shape == (height * width, 4)
    image_data = pyglet.image.ImageData(width, height, 'RGBA', dat.tostring())
    return image_data


def image_buffer_to_image(arr):
    import pyglet
    raw_data = np.empty((arr.get_width() * arr.get_height() * 3,), dtype='float32')
    arr.to_ndarray(raw_data.ctypes.data_as(ctypes.c_void_p).value)
    dat = (raw_data * 255.0).astype('uint8')
    dat.reshape((len(raw_data) / 3, 3))
    data_string = dat.tostring()
    image_data = pyglet.image.ImageData(arr.get_width(), arr.get_height(), 'RGB', data_string)
    return image_data


def image_buffer_to_ndarray(arr, bgr=False):
    channels = arr.get_channels()
    raw_data = np.empty((arr.get_width() * arr.get_height() * channels,), dtype='float32')
    arr.to_ndarray(raw_data.ctypes.data_as(ctypes.c_void_p).value)
    dat = raw_data.astype('float32')
    ret = dat.reshape((arr.get_width(), arr.get_height(), channels))
    if bgr:
        ret = ret[:, :, ::-1]
    return ret


def arange(x, y, d):
    while x < y:
        yield x
        x += d


def P(**kwargs):
    return config_from_dict(kwargs)


def imread(fn, bgr=False):
    img = taichi.core.Array2DVector3(0, 0, taichi.Vector(0.0, 0.0, 0.0))
    img.read(fn)
    return image_buffer_to_ndarray(img, bgr)[::-1]


def ndarray_to_array2d(array):
    if array.dtype == np.uint8:
        array = (array * (1 / 255.0)).astype(np.float32)
    assert array.dtype == np.float32
    array = array.copy()
    input_ptr = array.ctypes.data_as(ctypes.c_void_p).value
    if len(array.shape) == 2 or array.shape[2] == 1:
        arr = taichi.core.Array2Dreal(0, 0)
    elif array.shape[2] == 3:
        arr = taichi.core.Array2DVector3(0, 0, taichi.Vector(0, 0, 0))
    elif array.shape[2] == 4:
        arr = taichi.core.Array2DVector4(0, 0, taichi.Vector(0, 0, 0, 0))
    else:
        assert False, 'ndarray has to be n*m, n*m*3, or n*m*4'
    arr.from_ndarray(input_ptr, array.shape[0], array.shape[1])
    return arr


def array2d_to_ndarray(arr):
    if isinstance(arr, taichi.core.Array2DVector3):
        ndarray = np.empty((arr.get_width(), arr.get_height(), 3), dtype='float32')
    elif isinstance(arr, taichi.core.Array2DVector4):
        ndarray = np.empty((arr.get_width(), arr.get_height(), 4), dtype='float32')
    elif isinstance(arr, taichi.core.Array2Dreal):
        ndarray = np.empty((arr.get_width(), arr.get_height()), dtype='float32')
    else:
        assert False, 'Array2d must have type real, Vector3, or Vector4'
    output_ptr = ndarray.ctypes.data_as(ctypes.c_void_p).value
    arr.to_ndarray(output_ptr)
    return ndarray


def opencv_img_to_taichi_img(img):
    return (img.swapaxes(0, 1)[:, ::-1, ::-1] * (1 / 255.0)).astype(np.float32)
