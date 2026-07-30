from os.path import exists, join

from pythonforandroid.recipe import BootstrapNDKRecipe
from pythonforandroid.toolchain import current_directory, shprint
import sh


class LibSDL2Recipe(BootstrapNDKRecipe):
    version = "2.30.11"
    url = "https://github.com/libsdl-org/SDL/releases/download/release-{version}/SDL2-{version}.tar.gz"
    md5sum = 'bea190b480f6df249db29eb3bacfe41e'

    conflicts = ['sdl3']

    dir_name = 'SDL'

    depends = ['sdl2_image', 'sdl2_mixer', 'sdl2_ttf']

    def get_recipe_env(self, arch=None, with_flags_in_cc=True, with_python=True):
        env = super().get_recipe_env(
            arch=arch, with_flags_in_cc=with_flags_in_cc, with_python=with_python)
        env['APP_ALLOW_MISSING_DEPS'] = 'true'
        return env

    def should_build(self, arch):
        libdir = join(self.get_build_dir(arch.arch), '../..', 'libs', arch.arch)
        libs = ['libmain.so', 'libSDL2.so', 'libSDL2_image.so', 'libSDL2_mixer.so', 'libSDL2_ttf.so']
        return not all(exists(join(libdir, x)) for x in libs)

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        # 关闭 bionic FORTIFY：NDK r25+ 给 release 编 SDL2 默认启用 _FORTIFY_SOURCE=2，
        # SDL2 对已销毁 mutex 上锁会被 SIGABRT。强制 APP_OPTIM:=debug（NDK 不给 debug 加 FORTIFY）
        # 并显式 undef FORTIFY_SOURCE 作为双保险。
        jnidir = self.get_jni_dir()
        amk = join(jnidir, 'Application.mk')
        if exists(amk):
            c = open(amk).read()
            if "FORTIFY_SOURCE=0" not in c:
                c += (
                    "\n"
                    "# Patched by baibao local_recipes: disable bionic FORTIFY (SDL2 destroyed-mutex SIGABRT)\n"
                    "APP_OPTIM := debug\n"
                    "APP_CFLAGS += -D_FORTIFY_SOURCE=0\n"
                    "APP_CPPFLAGS += -D_FORTIFY_SOURCE=0\n"
                )
            open(amk, 'w').write(c)

        with current_directory(jnidir):
            shprint(
                sh.Command(join(self.ctx.ndk_dir, 'ndk-build')),
                'V=1',
                'NDK_DEBUG=' + ('1' if self.ctx.build_as_debuggable else '0'),
                _env=env
            )


recipe = LibSDL2Recipe()
