#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from abc import ABCMeta, abstractmethod

from devices.orange_pi import orange_pi
from devices.raspberry_pi import raspberry_pi
from pyfastogt import system_info, utils

# Script for building environment on clean machine

# Known issues
# For windows 32 please specify architecture 32

# defines
SDL_SRC_ROOT = "https://www.libsdl.org/release/"
SDL_IMAGE_SRC_ROOT = "https://www.libsdl.org/projects/SDL_image/release/"
SDL_TTF_SRC_ROOT = "https://www.libsdl.org/projects/SDL_ttf/release/"
OPENSSL_SRC_ROOT = "https://www.openssl.org/source/"

ARCH_OPENSSL_COMP = "gz"
ARCH_OPENSSL_EXT = "tar." + ARCH_OPENSSL_COMP
ARCH_SDL_COMP = "gz"
ARCH_SDL_EXT = "tar." + ARCH_SDL_COMP
FFMPEG_BRANCH = 'n3.4.2'

g_script_path = os.path.realpath(sys.argv[0])


def get_x11_libs(platform_name: str) -> list:
    dep_libs = []
    if platform_name == 'linux':
        distribution = system_info.linux_get_dist()
        if distribution == 'DEBIAN':
            dep_libs = ['libx11-dev', 'xorg-dev', 'xutils-dev', 'xserver-xorg', 'xinit']
        elif distribution == 'RHEL':
            dep_libs = ['libX11-devel', 'xorg-x11-server-devel', 'xorg-x11-server-source', 'xorg-x11-xinit']
    return dep_libs


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

    def system_libs(self, platform: system_info.Platform) -> list:  # additional system libs
        return self.system_platform_libs_.get(platform.name(), [])

    @abstractmethod
    def install_specific(self):
        pass


# description of ARMv6(armv6l) ARM11: ARMv6 - Architecture, armv6l - python platform.machine(), ARM11 - Holdings
# https://en.wikipedia.org/wiki/ARM_architecture

class PcDevice(SupportedDevice):  # Intel/AMD64 (i386/x86_64) Intel/Amd
    def __init__(self):
        SupportedDevice.__init__(self, 'pc', {'linux': [
            'libgl1-mesa-devel', 'libvdpau-devel', 'libva-devel',  # redhat
            'libgl1-mesa-dev', 'libvdpau-dev', 'libva-dev',  # debian
        ]}, utils.CompileInfo([], ['--disable-video-mir', '--disable-video-wayland', '--disable-sdltest']),
                                 utils.CompileInfo([], []))

    def install_specific(self):
        return


# Raspberry Pi
class RaspberryPiDevice(SupportedDevice):  # gles2, sdl2_ttf --without-x?
    def __init__(self, name):
        SupportedDevice.__init__(self, name, {'linux': ['libgl1-mesa-dev']},
                                 utils.CompileInfo([],
                                                   ['--host=arm-raspberry-linux-gnueabihf',
                                                    '--disable-pulseaudio', '--disable-esd',
                                                    '--disable-video-opengl', '--disable-video-opengles1',
                                                    '--enable-video-opengles2',
                                                    '--disable-video-mir', '--disable-video-wayland',
                                                    '--disable-video-x11', '--disable-sdltest']),
                                 utils.CompileInfo([], ['--enable-mmal', '--enable-decoder=h264_mmal', '--enable-omx',
                                                        '--enable-omx-rpi']))

    @abstractmethod
    def install_specific(self):
        pass


class RaspberryPi1ModelB(RaspberryPiDevice):  # ARMv6(armv6l) ARM11, omx/mmal
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi-model-b')

    def install_specific(self):
        raspberry_pi.install_raspberry_pi(256)


class RaspberryPi1ModelBPlus(RaspberryPiDevice):  # ARMv6(armv6l) ARM11, omx/mmal
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi-model-b+')

    def install_specific(self):
        raspberry_pi.install_raspberry_pi(256)


class RaspberryPi2ModelB(RaspberryPiDevice):  # ARMv8-A(aarch64) Cortex-A53, omx/mmal
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi2-model-b')

    def install_specific(self):
        raspberry_pi.install_raspberry_pi(512)


class RaspberryPi3ModelB(RaspberryPiDevice):  # ARMv8-A(aarch64) Cortex-A53, omx/mmal
    def __init__(self):
        RaspberryPiDevice.__init__(self, 'raspberry-pi3-model-b')

    def install_specific(self):
        raspberry_pi.install_raspberry_pi(512)


# Orange Pi
class OrangePiH3Device(SupportedDevice):  # gles2
    def __init__(self, name):
        SupportedDevice.__init__(self, name,
                                 {'linux': ['libgles2-mesa-dev', 'libcedrus1-dev', 'libpixman-1-dev',
                                            'xserver-xorg-video-fbturbo', 'xserver-xorg-legacy'
                                            ]},
                                 utils.CompileInfo(['patch/orange-pi/sdl2'],
                                                   ['--disable-pulseaudio', '--disable-esd',
                                                    '--disable-video-opengl', '--disable-video-opengles1',
                                                    '--enable-video-opengles2',
                                                    '--disable-video-mir', '--disable-video-wayland',
                                                    '--disable-sdltest']),
                                 utils.CompileInfo([], []))
        linux_libs = self.system_platform_libs_.get('linux')
        platform_name = system_info.get_os()
        linux_libs.extend(get_x11_libs(platform_name))

    def install_specific(self):
        orange_pi.install_orange_pi_h3()


class OrangePiOne(OrangePiH3Device):  # ARMv7-A(armv7l) Cortex-A7, vdpau/cedrus
    def __init__(self):
        OrangePiH3Device.__init__(self, 'orange-pi-one')


class OrangePiLite(OrangePiH3Device):  # ARMv7-A(armv7l) Cortex-A7, vdpau/cedrus
    def __init__(self):
        OrangePiH3Device.__init__(self, 'orange-pi-lite')


class OrangePiZeroPlus2H3(OrangePiH3Device):  # ARMv7-A(armv7l) Cortex-A7, vdpau/cedrus
    def __init__(self):
        OrangePiH3Device.__init__(self, 'orange-pi-zero-plus2-h3')


class OrangePiPC(OrangePiH3Device):  # ARMv7-A(armv7l) Cortex-A7, vdpau/cedrus
    def __init__(self):
        OrangePiH3Device.__init__(self, 'orange-pi-pc')


class OrangePiPlus2(OrangePiH3Device):  # ARMv7-A(armv7l) Cortex-A7, vdpau/cedrus
    def __init__(self):
        OrangePiH3Device.__init__(self, 'orange-pi-plus2')


class OrangePiPC2(SupportedDevice):  # ARMv8-A(aarch64) Cortex-A53
    def __init__(self, name='orange-pi-pc2'):
        SupportedDevice.__init__(self, name,
                                 {'linux': ['libgles2-mesa-dev']},
                                 utils.CompileInfo([], ['--disable-pulseaudio', '--disable-esd',
                                                        '--disable-video-opengl', '--disable-video-opengles1',
                                                        '--enable-video-opengles2',
                                                        '--disable-video-mir', '--disable-video-wayland',
                                                        '--disable-video-x11', '--disable-sdltest']),
                                 utils.CompileInfo([], []))

    def install_specific(self):
        orange_pi.install_orange_pi_h5()


class OrangePiZeroPlus2H5(OrangePiPC2):  # ARMv8-A(aarch64) Cortex-A53
    def __init__(self):
        OrangePiPC2.__init__(self, 'orange-pi-zero-plus2-h5')


SUPPORTED_DEVICES = [PcDevice(),
                     RaspberryPi1ModelB(), RaspberryPi1ModelBPlus(), RaspberryPi2ModelB(), RaspberryPi3ModelB(),
                     OrangePiOne(), OrangePiLite(), OrangePiZeroPlus2H3(), OrangePiPC(), OrangePiPlus2(), OrangePiPC2(),
                     OrangePiZeroPlus2H5()]


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
                dep_libs = ['git', 'gcc', 'g++', 'yasm', 'pkg-config', 'libtool', 'rpm',
                            'git', 'autogen', 'autoconf',
                            'cmake', 'make', 'ninja-build',
                            'libz-dev', 'libbz2-dev', 'libpcre3-dev',
                            'libasound2-dev',
                            'freetype-dev', 'libfreetype6-dev',
                            'libpng12-dev',
                            'libdrm-dev', 'libdri2-dev', 'libump-dev', 'libudev-dev',
                            'liblircclient-dev']
            elif distribution == 'RHEL':
                dep_libs = ['git', 'gcc', 'gcc-c++', 'yasm', 'pkgconfig', 'libtoolize', 'rpm-build',
                            'git', 'autogen', 'autoconf',
                            'cmake', 'make', 'ninja-build',
                            'zlib-devel', 'bzip2-devel', 'pcre-devel',
                            'alsa-lib-devel',
                            'freetype-devel', 'libfreetype6-devel',
                            'libpng12-devel',
                            'libdrm-devel', 'libdri2-devel', 'libump-devel', 'libudev-devel',
                            'liblircclient-devel']
                # x86_64 arch
                # Centos 7 no packages: libtoolize, libdri2-devel, libump-devel
                # Debian 8.7 no packages: libdri2-dev, libump-dev,
        elif platform_name == 'windows':
            if arch.name() == 'x86_64':
                dep_libs = ['git', 'make', 'mingw-w64-x86_64-gcc', 'mingw-w64-x86_64-yasm', 'mingw-w64-x86_64-ninja',
                            'mingw-w64-x86_64-make', 'mingw-w64-x86_64-cmake', 'mingw-w64-x86_64-freetype']
            elif arch.name() == 'i386':
                dep_libs = ['git', 'make', 'mingw-w64-i686-gcc', 'mingw-w64-i686-yasm', 'mingw-w64-i686-ninja',
                            'mingw-w64-i686-make', 'mingw-w64-i686-cmake', 'mingw-w64-i686-freetype']
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

    def build_ffmpeg(self):
        ffmpeg_platform_args = ['--disable-doc', '--pkg-config-flags=--static',
                                '--disable-programs', '--enable-openssl',
                                '--disable-opencl', '--disable-encoders',
                                '--disable-lzma', '--disable-iconv',
                                '--disable-shared', '--enable-static',
                                '--disable-debug', '--disable-jni', '--enable-postproc', '--enable-filter=yadif',
                                '--enable-avfilter', '--enable-avcodec', '--enable-avdevice', '--enable-avformat',
                                '--enable-swscale', '--enable-swresample',
                                '--extra-version=static']  # '--extra-cflags=--static'
        platform_name = self.platform_.name()
        if platform_name == 'linux':
            ffmpeg_platform_args.extend(['--disable-libxcb'])
        elif platform_name == 'windows':
            ffmpeg_platform_args = ffmpeg_platform_args
        elif platform_name == 'macosx':
            ffmpeg_platform_args.extend(['--cc=clang', '--cxx=clang++', '--disable-libxcb'])

        pwd = os.getcwd()
        compiler_flags = self.device_.ffmpeg_compile_info()
        compiler_flags.extend_flags(ffmpeg_platform_args)
        cloned_dir = utils.git_clone('https://github.com/fastogt/ffmpeg.git', pwd)
        os.chdir(cloned_dir)
        utils.build_command_configure(compiler_flags, g_script_path, self.prefix_path_)
        os.chdir(pwd)
        shutil.rmtree(cloned_dir)

    def build_sdl2(self, version):
        compiler_flags = self.device_.sdl2_compile_info()
        self.build('{0}SDL2-{1}.{2}'.format(SDL_SRC_ROOT, version, ARCH_SDL_EXT), compiler_flags)

    def build_sdl2_image(self, version):
        compiler_flags = utils.CompileInfo([], ['--disable-svg', '--disable-sdltest', '--disable-bmp', '--disable-gif',
                                                '--disable-jpg', '--disable-lbm', '--disable-pcx', '--disable-pnm',
                                                '--disable-tga', '--disable-tif', '--disable-xcf', '--disable-xpm',
                                                '--disable-xv', '-disable-webp'])
        self.build('{0}SDL2_image-{1}.{2}'.format(SDL_IMAGE_SRC_ROOT, version, ARCH_SDL_EXT), compiler_flags)

    def build_sdl2_ttf(self, version):
        compiler_flags = utils.CompileInfo([], ['--disable-sdltest'])
        self.build('{0}SDL2_ttf-{1}.{2}'.format(SDL_TTF_SRC_ROOT, version, ARCH_SDL_EXT), compiler_flags)

    def build_openssl(self, version):
        compiler_flags = utils.CompileInfo([], ['no-shared'])
        url = '{0}openssl-{1}.{2}'.format(OPENSSL_SRC_ROOT, version, ARCH_OPENSSL_EXT)
        self.build(url, compiler_flags, './config')

    def build_common(self):
        pwd = os.getcwd()
        cmake_project_root_abs_path = '..'
        if not os.path.exists(cmake_project_root_abs_path):
            raise utils.BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

        # project static options
        prefix_args = '-DCMAKE_INSTALL_PREFIX={0}'.format(self.prefix_path_)

        cmake_line = ['cmake', cmake_project_root_abs_path, '-GNinja', '-DCMAKE_BUILD_TYPE=RELEASE',
                      prefix_args]
        try:
            cloned_dir = utils.git_clone('https://github.com/fastogt/common.git', pwd)
            os.chdir(cloned_dir)

            os.mkdir('build_cmake_release')
            os.chdir('build_cmake_release')
            common_cmake_line = list(cmake_line)
            common_cmake_line.append('-DQT_ENABLED=OFF')
            common_cmake_line.append('-DJSON_ENABLED=ON')
            subprocess.call(common_cmake_line)
            subprocess.call(['ninja', 'install'])
            os.chdir(self.build_dir_path_)
            shutil.rmtree(cloned_dir)
        except Exception as ex:
            os.chdir(self.build_dir_path_)
            raise ex

    def build_fastoplayer(self):
        pwd = os.getcwd()
        cmake_project_root_abs_path = '..'
        if not os.path.exists(cmake_project_root_abs_path):
            raise utils.BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

        # project static options
        prefix_args = '-DCMAKE_INSTALL_PREFIX={0}'.format(self.prefix_path_)

        cmake_line = ['cmake', cmake_project_root_abs_path, '-GNinja', '-DCMAKE_BUILD_TYPE=RELEASE',
                      prefix_args]
        try:
            cloned_dir = utils.git_clone('https://github.com/fastogt/fastoplayer.git', pwd)
            os.chdir(cloned_dir)

            os.mkdir('build_cmake_release')
            os.chdir('build_cmake_release')
            fastoplayer_cmake_line = list(cmake_line)
            fastoplayer_cmake_line.append('-DBUILD_PLAYER=OFF')
            subprocess.call(fastoplayer_cmake_line)
            subprocess.call(['ninja', 'install'])
            os.chdir(self.build_dir_path_)
            shutil.rmtree(cloned_dir)
        except Exception as ex:
            os.chdir(self.build_dir_path_)
            raise ex

    def build_libev(self):
        libev_compiler_flags = utils.CompileInfo([], ['--with-pic', '--disable-shared', '--enable-static'])

        pwd = os.getcwd()
        cloned_dir = utils.git_clone('https://github.com/fastogt/libev.git', pwd)
        os.chdir(cloned_dir)

        autogen_libev = ['sh', 'autogen.sh']
        subprocess.call(autogen_libev)

        utils.build_command_configure(libev_compiler_flags, g_script_path, self.prefix_path_)
        os.chdir(pwd)
        shutil.rmtree(cloned_dir)

    def build_jsonc(self):
        jsonc_compiler_flags = utils.CompileInfo([], ['--disable-shared', '--enable-static'])

        pwd = os.getcwd()
        cloned_dir = utils.git_clone('https://github.com/fastogt/json-c.git', pwd)
        os.chdir(cloned_dir)

        autogen_jsonc = ['sh', 'autogen.sh']
        subprocess.call(autogen_jsonc)

        utils.build_command_configure(jsonc_compiler_flags, g_script_path, self.prefix_path_)
        os.chdir(pwd)
        shutil.rmtree(cloned_dir)

    def build_snappy(self):
        pwd = os.getcwd()
        cmake_project_root_abs_path = '..'
        if not os.path.exists(cmake_project_root_abs_path):
            raise utils.BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

        # project static options
        prefix_args = '-DCMAKE_INSTALL_PREFIX={0}'.format(self.prefix_path_)

        cmake_line = ['cmake', cmake_project_root_abs_path, '-GNinja', '-DCMAKE_BUILD_TYPE=RELEASE',
                      '-DBUILD_SHARED_LIBS=OFF', '-DSNAPPY_BUILD_TESTS=OFF',
                      prefix_args]
        try:
            cloned_dir = utils.git_clone('https://github.com/fastogt/snappy.git', pwd)
            os.chdir(cloned_dir)

            os.mkdir('build_cmake_release')
            os.chdir('build_cmake_release')
            snappy_cmake_line = list(cmake_line)
            subprocess.call(snappy_cmake_line)
            subprocess.call(['ninja', 'install'])
            os.chdir(self.build_dir_path_)
            shutil.rmtree(cloned_dir)
        except Exception as ex:
            os.chdir(self.build_dir_path_)
            raise ex


if __name__ == "__main__":
    sdl2_default_version = '2.0.8'
    sdl2_image_default_version = '2.0.1'
    sdl2_ttf_default_version = '2.0.14'
    openssl_default_version = '1.1.0h'

    host_os = system_info.get_os()
    arch_host_os = system_info.get_arch_name()
    default_device = get_device().name()
    availible_devices = get_available_devices()

    parser = argparse.ArgumentParser(prog='build_env', usage='%(prog)s [options]')

    # system
    system_grp = parser.add_mutually_exclusive_group()
    system_grp.add_argument('--with-system', help='build with system dependencies (default)', dest='with_system',
                            action='store_true', default=True)
    system_grp.add_argument('--without-system', help='build without system dependencies', dest='with_system',
                            action='store_false', default=False)

    # device
    device_grp = parser.add_mutually_exclusive_group()
    device_grp.add_argument('--with-device',
                            help='build dependencies for device (default, device:{0})'.format(default_device),
                            dest='with_device', action='store_true', default=True)
    device_grp.add_argument('--without-device', help='build without device dependencies', dest='with_device',
                            action='store_false', default=False)
    parser.add_argument('--device',
                        help='device (default: {0}, available: {1})'.format(default_device, availible_devices),
                        default=default_device)

    # snappy
    snappy_grp = parser.add_mutually_exclusive_group()
    snappy_grp.add_argument('--with-snappy', help='build snappy (default, version: git master)', dest='with_snappy',
                            action='store_true', default=True)
    snappy_grp.add_argument('--without-snappy', help='build without snappy', dest='with_snappy', action='store_false',
                            default=False)

    # json-c
    jsonc_grp = parser.add_mutually_exclusive_group()
    jsonc_grp.add_argument('--with-json-c', help='build json-c (default, version: git master)', dest='with_jsonc',
                           action='store_true', default=True)
    jsonc_grp.add_argument('--without-json-c', help='build without json-c', dest='with_jsonc', action='store_false',
                           default=False)

    # libev
    libev_grp = parser.add_mutually_exclusive_group()
    libev_grp.add_argument('--with-libev-c', help='build libev (default, version: git master)', dest='with_libev',
                           action='store_true', default=True)
    libev_grp.add_argument('--without-libev-c', help='build without libev', dest='with_libev', action='store_false',
                           default=False)

    # common
    common_grp = parser.add_mutually_exclusive_group()
    common_grp.add_argument('--with-common', help='build common (default, version: git master)', dest='with_common',
                            action='store_true', default=True)
    common_grp.add_argument('--without-common', help='build without common', dest='with_common', action='store_false',
                            default=False)

    # fastoplayer
    fastoplayer_grp = parser.add_mutually_exclusive_group()
    fastoplayer_grp.add_argument('--with-fastoplayer', help='build fastoplayer (default, version: git master)',
                                 dest='with_fastoplayer',
                                 action='store_true', default=True)
    fastoplayer_grp.add_argument('--without-fastoplayer', help='build without fastoplayer', dest='with_fastoplayer',
                                 action='store_false',
                                 default=False)

    # sdl2
    sdl2_grp = parser.add_mutually_exclusive_group()
    sdl2_grp.add_argument('--with-sdl2', help='build sdl2 (default, version:{0})'.format(sdl2_default_version),
                          dest='with_sdl2', action='store_true', default=True)
    sdl2_grp.add_argument('--without-sdl2', help='build without sdl2', dest='with_sdl2', action='store_false',
                          default=False)
    parser.add_argument('--sdl2-version', help='sdl2 version (default: {0})'.format(sdl2_default_version),
                        default=sdl2_default_version)

    # sdl2_image
    sdl2_image_grp = parser.add_mutually_exclusive_group()
    sdl2_image_grp.add_argument('--with-sdl2_image',
                                help='build sdl2_image (default, version:{0})'.format(sdl2_image_default_version),
                                dest='with_sdl2_image', action='store_true', default=True)
    sdl2_image_grp.add_argument('--without-sdl2-image', help='build without sdl2 image', dest='with_sdl2_image',
                                action='store_false',
                                default=False)
    parser.add_argument('--sdl2-image-version',
                        help='sdl2 image version (default: {0})'.format(sdl2_image_default_version),
                        default=sdl2_image_default_version)

    # sdl2_ttf
    sdl2_ttf_grp = parser.add_mutually_exclusive_group()
    sdl2_ttf_grp.add_argument('--with-sdl2_ttf',
                              help='build sdl2_ttf (default, version:{0})'.format(sdl2_ttf_default_version),
                              dest='with_sdl2_ttf', default=True)
    sdl2_ttf_grp.add_argument('--without-sdl2-ttf', help='build without sdl2 ttf', dest='with_sdl2_ttf',
                              action='store_false',
                              default=False)
    parser.add_argument('--sdl2-ttf-version', help='sdl2 ttf version (default: {0})'.format(sdl2_ttf_default_version),
                        default=sdl2_ttf_default_version)

    # openssl
    openssl_grp = parser.add_mutually_exclusive_group()
    openssl_grp.add_argument('--with-openssl',
                             help='build openssl (default, version:{0})'.format(openssl_default_version),
                             dest='with_openssl', action='store_true', default=True)
    openssl_grp.add_argument('--without-openssl', help='build without openssl', dest='with_openssl',
                             action='store_false',
                             default=False)
    parser.add_argument('--openssl-version', help='openssl version (default: {0})'.format(openssl_default_version),
                        default=openssl_default_version)

    # ffmpeg
    ffmpeg_grp = parser.add_mutually_exclusive_group()
    ffmpeg_grp.add_argument('--with-ffmpeg', help='build ffmpeg (default, version: git master)', dest='with_ffmpeg',
                            action='store_true', default=True)
    ffmpeg_grp.add_argument('--without-ffmpeg', help='build without ffmpeg', dest='with_ffmpeg', action='store_false',
                            default=False)

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

    if argv.with_snappy:
        request.build_snappy()
    if argv.with_libev:
        request.build_libev()
    if argv.with_jsonc:
        request.build_jsonc()
    if argv.with_common:
        request.build_common()

    if argv.with_sdl2:
        request.build_sdl2(argv.sdl2_version)
    if argv.with_sdl2_image:
        request.build_sdl2_image(argv.sdl2_image_version)
    if argv.with_sdl2_ttf:
        request.build_sdl2_ttf(argv.sdl2_ttf_version)

    if argv.with_openssl:
        request.build_openssl(argv.openssl_version)

    if argv.with_ffmpeg:
        request.build_ffmpeg()

    if argv.with_fastoplayer:
        request.build_fastoplayer()
