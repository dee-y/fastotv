#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod

from devices.orange_pi import orange_pi
from devices.raspberry_pi import raspberry_pi
from pybuild_utils.base import system_info, utils

# Script for building environment on clean machine

# Known issues
# For windows 32 please specify architecture 32

# defines
CMAKE_SRC_ROOT = "https://cmake.org/files/"
SDL_SRC_ROOT = "https://www.libsdl.org/release/"
SDL_TTF_SRC_ROOT = "https://www.libsdl.org/projects/SDL_ttf/release/"
FFMPEG_SRC_ROOT = "http://ffmpeg.org/releases/"
PNG_SRC_ROOT = "https://sourceforge.net/projects/libpng/files/libpng16/older-releases/"
OPENSSL_SRC_ROOT = "https://www.openssl.org/source/"

ARCH_CMAKE_COMP = "gz"
ARCH_CMAKE_EXT = "tar." + ARCH_CMAKE_COMP
ARCH_PNG_COMP = "gz"
ARCH_PNG_EXT = "tar." + ARCH_PNG_COMP
ARCH_OPENSSL_COMP = "gz"
ARCH_OPENSSL_EXT = "tar." + ARCH_OPENSSL_COMP
ARCH_SDL_COMP = "gz"
ARCH_SDL_EXT = "tar." + ARCH_SDL_COMP
ARCH_FFMPEG_COMP = "bz2"
ARCH_FFMPEG_EXT = "tar." + ARCH_FFMPEG_COMP

g_script_path = os.path.realpath(sys.argv[0])


def splitext(path):
    for ext in ['.tar.gz', '.tar.bz2', '.tar.xz']:
        if path.endswith(ext):
            return path[:-len(ext)]
    return os.path.splitext(path)[0]


class SupportedDevice(metaclass=ABCMeta):
    def __init__(self, name, system_platform_libs: dict, sdl2_compile_info, ffmpeg_compile_info):
        self.name_ = name
        self.system_platform_libs_ = system_platform_libs
        self.sdl2_compile_info_ = sdl2_compile_info
        self.ffmpeg_compile_info_ = ffmpeg_compile_info

    def name(self):
        return self.name_

    def sdl2_compile_info(self):
        return self.sdl2_compile_info_

    def ffmpeg_compile_info(self):
        return self.ffmpeg_compile_info_

    def system_libs(self, platform: system_info.Platform) -> list:
        return self.system_platform_libs_.get(platform.name(), [])

    @abstractmethod
    def install_specific(self):
        pass


# PC
class PcDevice(SupportedDevice):
    def __init__(self):
        SupportedDevice.__init__(self, 'pc', {'linux': [
            'libvdpau-devel', 'libva-devel', 'libgl1-mesa-devel',  # redhat
            'libvdpau-dev', 'libva-dev', 'libgl1-mesa-dev'  # debian
        ]}, utils.CompileInfo([], []), utils.CompileInfo([], []))

    def install_specific(self):
        return


# Raspberry Pi
class RaspberryPiDevice(SupportedDevice):  # gles2
    def __init__(self, name):
        SupportedDevice.__init__(self, name, {'linux': []},
                                 utils.CompileInfo([], ['--disable-video-opengl', '--disable-video-opengles1',
                                                        '--enable-video-opengles2']),
                                 utils.CompileInfo([], ['--enable-mmal', '--enable-decoder=h264_mmal', '--enable-omx',
                                                        '--enable-omx-rpi']))

    def install_specific(self):
        raspberry_pi.install_raspberry_pi()


class RaspberryPi1ModelB(RaspberryPiDevice):
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi-model-b')


class RaspberryPi1ModelBPlus(RaspberryPiDevice):  # armv6l
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi-model-b+')


# Orange Pi
class OrangePiDevice(SupportedDevice):  # gles2
    def __init__(self, name):
        SupportedDevice.__init__(self, name,
                                 {'linux': ['libgles2-mesa-dev', 'libgl1-mesa-dev',
                                            'xserver-xorg-video-fbturbo', 'xserver-xorg-legacy',
                                            'libcedrus1-dev']},
                                 utils.CompileInfo(['patch/orange-pi/sdl2'],
                                                   ['--disable-video-opengl', '--disable-video-opengles1',
                                                    '--enable-video-opengles2']),
                                 utils.CompileInfo([], []))

    def install_specific(self):
        orange_pi.install_orange_pi()


class OrangePiOne(OrangePiDevice):  # armv7l, vdpau/cedrus
    def __init__(self):
        OrangePiDevice.__init__(self, 'orange-pi-one')


class OrangePiLite(OrangePiDevice):  # armv7l, vdpau/cedrus
    def __init__(self):
        OrangePiDevice.__init__(self, 'orange-pi-lite')
        linux_libs = self.system_platform_libs_.get('linux')
        linux_libs.extend(['liblircclient-dev'])


class OrangePiPC(OrangePiDevice):  # armv7l, vdpau/cedrus
    def __init__(self):
        OrangePiDevice.__init__(self, 'orange-pi-pc')
        linux_libs = self.system_platform_libs_.get('linux')
        linux_libs.extend(['liblircclient-dev'])


class OrangePiPlus2(OrangePiDevice):  # armv7l, vdpau/cedrus
    def __init__(self):
        OrangePiDevice.__init__(self, 'orange-pi-plus2')
        linux_libs = self.system_platform_libs_.get('linux')
        linux_libs.extend(['liblircclient-dev'])


SUPPORTED_DEVICES = [PcDevice(),
                     RaspberryPi1ModelB(), RaspberryPi1ModelBPlus(),
                     OrangePiOne(), OrangePiLite(), OrangePiPC(), OrangePiPlus2()]


def get_device() -> SupportedDevice:
    return SUPPORTED_DEVICES[0]


def get_supported_device_by_name(name) -> SupportedDevice:
    return next((x for x in SUPPORTED_DEVICES if x.name() == name), None)


def get_available_devices() -> list:
    result = []
    for dev in SUPPORTED_DEVICES:
        result.extend([dev.name()])
    return result


class BuildRequest(object):
    def __init__(self, device, platform, arch_name, dir_path, prefix_path):
        platform_or_none = system_info.get_supported_platform_by_name(platform)

        if not platform_or_none:
            raise utils.BuildError('invalid platform')

        build_arch = platform_or_none.architecture_by_arch_name(arch_name)
        if not build_arch:
            raise utils.BuildError('invalid arch')

        if not prefix_path:
            prefix_path = build_arch.default_install_prefix_path()

        packages_types = platform_or_none.package_types()
        build_platform = platform_or_none.make_platform_by_arch(build_arch, packages_types)

        self.device_ = device
        self.platform_ = build_platform
        build_dir_path = os.path.abspath(dir_path)
        if os.path.exists(build_dir_path):
            shutil.rmtree(build_dir_path)

        os.mkdir(build_dir_path)
        os.chdir(build_dir_path)

        self.build_dir_path_ = build_dir_path
        self.prefix_path_ = prefix_path
        print(
            "Build request for device: {0}, platform: {1}({2}) created".format(device.name(), build_platform.name(),
                                                                               build_arch.name()))

    def install_device_specific(self):
        self.device_.install_specific()

    def get_system_libs(self):
        platform = self.platform_
        platform_name = platform.name()
        arch = platform.arch()
        dep_libs = []

        if platform_name == 'linux':
            distribution = system_info.linux_get_dist()
            if distribution == 'DEBIAN':
                dep_libs = ['git', 'gcc', 'g++', 'yasm', 'ninja-build', 'pkg-config', 'libtool', 'rpm', 'make',
                            'libz-dev', 'libbz2-dev', 'libpcre3-dev',
                            'libasound2-dev',
                            'freetype-dev',
                            'libx11-dev',
                            'libdrm-dev', 'libdri2-dev', 'libump-dev',
                            'xorg-dev', 'xutils-dev', 'xserver-xorg', 'xinit']
            elif distribution == 'RHEL':
                dep_libs = ['git', 'gcc', 'gcc-c++', 'yasm', 'ninja-build', 'pkgconfig', 'libtoolize', 'rpm-build',
                            'make',
                            'zlib-devel', 'bzip2-devel', 'pcre-devel',
                            'alsa-lib-devel',
                            'freetype-devel',
                            'libX11-devel',
                            'libdrm-devel', 'libdri2-devel', 'libump-devel',
                            'xorg-x11-server-devel', 'xorg-x11-server-source', 'xorg-x11-xinit']
                # x86_64 arch
                # Centos 7 no packages: libtoolize, libdri2-devel, libump-devel
                # Debian 8.7 no packages: libdri2-dev, libump-dev,
        elif platform_name == 'windows':
            if arch.name() == 'x86_64':
                dep_libs = ['git', 'make', 'mingw-w64-x86_64-gcc', 'mingw-w64-x86_64-yasm',
                            'mingw-w64-x86_64-make', 'mingw-w64-x86_64-ninja', 'mingw-w64-x86_64-freetype']
            elif arch.name() == 'i386':
                dep_libs = ['git', 'make', 'mingw-w64-i686-gcc', 'mingw-w64-i686-yasm',
                            'mingw-w64-i686-make', 'mingw-w64-i686-ninja', 'mingw-w64-i686-freetype']
        elif platform_name == 'macosx':
            dep_libs = ['git', 'yasm', 'make', 'ninja', 'freetype']
        else:
            raise NotImplemented("Unknown platform '%s'" % platform_name)

        device_specific_libs = self.device_.system_libs(platform)
        dep_libs.extend(device_specific_libs)
        return dep_libs

    def install_system(self):
        platform = self.platform_
        dep_libs = self.get_system_libs()
        for lib in dep_libs:
            platform.install_package(lib)

        # post install step
        platform_name = platform.name()
        if platform_name == 'linux':
            distribution = system_info.linux_get_dist()
            if distribution == 'RHEL':
                subprocess.call(['ln', '-sf', '/usr/bin/ninja-build', '/usr/bin/ninja'])

    def build(self, url, compiler_flags: utils.CompileInfo, executable='./configure'):
        utils.build_from_sources(url, compiler_flags, g_script_path, self.prefix_path_, executable)

    def build_ffmpeg(self, version):
        ffmpeg_platform_args = ['--disable-doc',
                                '--disable-programs',  # '--enable-openssl',
                                '--disable-opencl', '--disable-encoders',
                                '--disable-lzma', '--disable-iconv',
                                '--disable-shared', '--enable-static',
                                '--disable-debug', '--disable-jni',
                                '--enable-avfilter', '--enable-avcodec', '--enable-avdevice', '--enable-avformat',
                                '--enable-swscale', '--enable-swresample',
                                '--extra-version=static']  # '--extra-cflags=--static'
        platform_name = self.platform_.name()
        if platform_name == 'linux':
            ffmpeg_platform_args.extend(['--disable-libxcb'])
        elif platform_name == 'windows':
            ffmpeg_platform_args = ffmpeg_platform_args
        elif platform_name == 'macosx':
            ffmpeg_platform_args.extend(['--cc=clang', '--cxx=clang++'])

        compiler_flags = self.device_.ffmpeg_compile_info()
        compiler_flags.extend_flags(ffmpeg_platform_args)
        self.build('{0}ffmpeg-{1}.{2}'.format(FFMPEG_SRC_ROOT, version, ARCH_FFMPEG_EXT), compiler_flags)

    def build_sdl2(self, version):
        compiler_flags = self.device_.sdl2_compile_info()
        self.build('{0}SDL2-{1}.{2}'.format(SDL_SRC_ROOT, version, ARCH_SDL_EXT), compiler_flags)

    def build_sdl2_ttf(self, version):
        compiler_flags = utils.CompileInfo([], [])
        self.build('{0}SDL2_ttf-{1}.{2}'.format(SDL_TTF_SRC_ROOT, version, ARCH_SDL_EXT), compiler_flags)

    def build_openssl(self, version):
        compiler_flags = utils.CompileInfo([], ['no-shared'])
        url = '{0}openssl-{1}.{2}'.format(OPENSSL_SRC_ROOT, version, ARCH_OPENSSL_EXT)
        print(url)
        self.build(url, compiler_flags, './config')

    def build_libpng(self, version):
        compiler_flags = utils.CompileInfo([], [])
        self.build('{0}{1}/libpng-{1}.{2}'.format(PNG_SRC_ROOT, version, ARCH_PNG_EXT), compiler_flags)

    def build_cmake(self, version):
        stabled_version_array = version.split(".")
        stabled_version = 'v{0}.{1}'.format(stabled_version_array[0], stabled_version_array[1])
        compiler_flags = utils.CompileInfo([], [])
        self.build('{0}{1}/cmake-{2}.{3}'.format(CMAKE_SRC_ROOT, stabled_version, version, ARCH_CMAKE_EXT, []),
                   compiler_flags)

    def build_common(self):
        pwd = os.getcwd()
        cmake_project_root_abs_path = '..'
        if not os.path.exists(cmake_project_root_abs_path):
            raise utils.BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

        # project static options
        prefix_args = '-DCMAKE_INSTALL_PREFIX={0}'.format(self.prefix_path_)

        cmake_line = ['cmake', cmake_project_root_abs_path, '-GUnix Makefiles', '-DCMAKE_BUILD_TYPE=RELEASE',
                      prefix_args]
        try:
            cloned_dir = utils.git_clone('https://github.com/fastogt/common.git', pwd)
            os.chdir(cloned_dir)

            os.mkdir('build_cmake_release')
            os.chdir('build_cmake_release')
            common_cmake_line = list(cmake_line)
            common_cmake_line.append('-DQT_ENABLED=OFF')
            subprocess.call(common_cmake_line)
            subprocess.call(['make', 'install'])
            os.chdir(self.build_dir_path_)
            shutil.rmtree(cloned_dir)
        except Exception as ex:
            os.chdir(self.build_dir_path_)
            raise ex


if __name__ == "__main__":
    libpng_default_version = '1.6.21'
    sdl2_default_version = '2.0.5'
    sdl2_ttf_default_version = '2.0.14'
    openssl_default_version = '1.0.2l'
    ffmpeg_default_version = '3.3'
    cmake_default_version = '3.8.1'

    host_os = system_info.get_os()
    arch_host_os = system_info.get_arch_name()
    default_device = get_device().name()
    availible_devices = get_available_devices()

    parser = argparse.ArgumentParser(prog='build_env', usage='%(prog)s [options]')
    parser.add_argument('--with-device',
                        help='build dependencies for device (default, device:{0})'.format(default_device),
                        dest='with_device', action='store_true')
    parser.add_argument('--without-device', help='build without device dependencies', dest='with_device',
                        action='store_false')
    parser.add_argument('--device',
                        help='device (default: {0}, available: {1})'.format(default_device, availible_devices),
                        default=default_device)
    parser.set_defaults(with_device=True)

    parser.add_argument('--with-system', help='build with system dependencies (default)', dest='with_system',
                        action='store_true')
    parser.add_argument('--without-system', help='build without system dependencies', dest='with_system',
                        action='store_false')
    parser.set_defaults(with_system=True)

    parser.add_argument('--with-libpng', help='build libpng (default, version:{0})'.format(libpng_default_version),
                        dest='with_libpng', action='store_true')
    parser.add_argument('--without-libpng', help='build without libpng', dest='with_libpng', action='store_false')
    parser.add_argument('--libpng-version', help='libpng version (default: {0})'.format(libpng_default_version),
                        default=libpng_default_version)
    parser.set_defaults(with_libpng=True)

    parser.add_argument('--with-sdl2', help='build sdl2 (default, version:{0})'.format(sdl2_default_version),
                        dest='with_sdl2', action='store_true')
    parser.add_argument('--without-sdl2', help='build without sdl2', dest='with_sdl2', action='store_false')
    parser.add_argument('--sdl2-version', help='sdl2 version (default: {0})'.format(sdl2_default_version),
                        default=sdl2_default_version)
    parser.set_defaults(with_sdl2=True)

    parser.add_argument('--with-sdl2_ttf', help='build sdl2 (default, version:{0})'.format(sdl2_ttf_default_version),
                        dest='with_sdl2-ttf', action='store_true')
    parser.add_argument('--without-sdl2-ttf', help='build without sdl2 ttf', dest='with_sdl2_ttf', action='store_false')
    parser.add_argument('--sdl2-ttf-version', help='sdl2 ttf version (default: {0})'.format(sdl2_ttf_default_version),
                        default=sdl2_ttf_default_version)
    parser.set_defaults(with_sdl2_ttf=True)

    parser.add_argument('--with-openssl', help='build openssl (default, version:{0})'.format(openssl_default_version),
                        dest='with_openssl', action='store_true')
    parser.add_argument('--without-openssl', help='build without openssl', dest='with_openssl', action='store_false')
    parser.add_argument('--openssl-version', help='openssl version (default: {0})'.format(openssl_default_version),
                        default=openssl_default_version)
    parser.set_defaults(with_openssl=True)

    parser.add_argument('--with-ffmpeg', help='build ffmpeg (default, version:{0})'.format(ffmpeg_default_version),
                        dest='with_ffmpeg', action='store_true')
    parser.add_argument('--without-ffmpeg', help='build without ffmpeg', dest='with_ffmpeg', action='store_false')
    parser.add_argument('--ffmpeg-version', help='ffmpeg version (default: {0})'.format(ffmpeg_default_version),
                        default=ffmpeg_default_version)
    parser.set_defaults(with_ffmpeg=True)

    parser.add_argument('--with-cmake', help='build cmake (default, version:{0})'.format(cmake_default_version),
                        dest='with_cmake', action='store_true')
    parser.add_argument('--without-cmake', help='build without cmake', dest='with_cmake', action='store_false')
    parser.add_argument('--cmake-version', help='cmake version (default: {0})'.format(cmake_default_version),
                        default=cmake_default_version)
    parser.set_defaults(with_cmake=True)

    parser.add_argument('--with-common', help='build common (default, version: git master)', dest='with_common',
                        action='store_true')
    parser.add_argument('--without-common', help='build without common', dest='with_common', action='store_false')
    parser.set_defaults(with_common=True)

    parser.add_argument('--platform', help='build for platform (default: {0})'.format(host_os), default=host_os)
    parser.add_argument('--architecture', help='architecture (default: {0})'.format(arch_host_os),
                        default=arch_host_os)
    parser.add_argument('--prefix_path', help='prefix_path (default: None)', default=None)

    argv = parser.parse_args()

    arg_platform = argv.platform
    arg_prefix_path = argv.prefix_path
    arg_architecture = argv.architecture
    sup_device = get_supported_device_by_name(argv.device)
    if not sup_device:
        raise utils.BuildError('invalid device')

    request = BuildRequest(sup_device, arg_platform, arg_architecture, 'build_' + arg_platform + '_env',
                           arg_prefix_path)
    if argv.with_system:
        request.install_system()

    if argv.with_device:
        request.install_device_specific()

    if argv.with_libpng:
        request.build_libpng(argv.libpng_version)

    if argv.with_cmake:
        request.build_cmake(argv.cmake_version)
    if argv.with_common:
        request.build_common()

    if argv.with_sdl2:
        request.build_sdl2(argv.sdl2_version)
    if argv.with_sdl2_ttf:
        request.build_sdl2_ttf(argv.sdl2_ttf_version)
    if argv.with_openssl:
        request.build_openssl(argv.openssl_version)
    if argv.with_ffmpeg:
        request.build_ffmpeg(argv.ffmpeg_version)
