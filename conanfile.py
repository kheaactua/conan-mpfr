import os, shutil
from conans import ConanFile, AutoToolsBuildEnvironment, tools

class MpfrConan(ConanFile):
    """ Building MPFR for the intention of using it to build CGAL """

    name        = 'mpfr'
    version     = '4.0.1'
    md5hash     = 'a2a6d97d890222a29d9b7683d075b97b'
    description = 'The GNU Multiple Precision Arithmetic Library'
    url         = 'http://www.mpfr.org/mpfr-current'
    license     = 'MIT'
    settings    = 'os', 'compiler', 'arch', 'build_type'
    requires    = 'gmp/[>=5.0.0]@ntc/stable', 'helpers/0.3@ntc/stable'

    # See http://www.mpfr.org/mpfr-current/mpfr.pdf for other potential options
    options = {
        'shared':            [True, False],
        'static':            [True, False],
        'msvc':              [12, 15],
    }
    default_options = 'shared=True', 'static=True', 'msvc=12'

    def source(self):
        archive = 'mpfr-{version}.tar.gz'.format(version=self.version)
        tools.download('http://www.mpfr.org/mpfr-current/{archive}'.format(archive=archive), archive)
        tools.check_md5(archive, self.md5hash)
        tools.unzip(archive)
        shutil.move('mpfr-{version}'.format(version=self.version), self.name)
        os.unlink(archive)

    def configure(self):
        if tools.os_info.is_windows:
            # On Windows, we can only build the static OR shared
            self.options.static = not self.options.shared

            # Shared MPFR requires a GMP DLL
            self.options['gmp'].shared = self.options.shared

    def build(self):
        with tools.chdir(self.name):
            autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)

            env_vars = {}
            args = []

            if 'gcc' == self.settings.compiler and tools.os_info.is_windows:
                args.append('--prefix=%s'%tools.unix_path(self.package_folder))
            else:
                args.append('--prefix=%s'%self.package_folder)

            args.append('--%s-shared'%('enable' if self.options.shared else 'disable'))
            args.append('--%s-static'%('enable' if self.options.static else 'disable'))

            if tools.os_info.is_linux or self.settings.os == "Macos":
                autotools.fpic = True
                if self.settings.arch == 'x86':
                    env_vars['ABI'] = '32'
                    autotools.cxx_flags.append('-m32')

            # Add GMP
            autotools.library_paths.append(os.path.join(self.deps_cpp_info['gmp'].rootpath, self.deps_cpp_info['gmp'].libdirs[0]))
            autotools.include_paths.append(os.path.join(self.deps_cpp_info['gmp'].rootpath, self.deps_cpp_info['gmp'].includedirs[0]))

            # Debug
            self.output.info('Configure arguments: %s'%' '.join(args))

            # Set up our build environment
            with tools.environment_append(env_vars):
                autotools.configure(args=args)

            autotools.make()
            autotools.make(args=['install'])

    def package_info(self):
        # For now, don't export the lib
        # self.cpp_info.libs = tools.collect_libs(self)

        # Populate the pkg-config environment variables
        with tools.pythonpath(self): # Compensate for #2644
            from platform_helpers import adjustPath, appendPkgConfigPath

            self.env_info.PKG_CONFIG_MPFR_PREFIX = adjustPath(self.package_folder)
            appendPkgConfigPath(adjustPath(os.path.join(self.package_folder, 'lib', 'pkgconfig')), self.env_info)

        # self.cpp_info.libs = tools.collect_libs(self)

    def package_id(self):
        # On windows, we cross compile this with mingw.. But because it's
        # compatible with MSVC, set it's hash to reflect that.
        # Maybe use tools.cross_building(self.settings)
        if 'gcc' == self.settings.compiler and tools.os_info.is_windows:
            self.info.settings.compiler = 'Visual Studio'
            self.info.settings.compiler.version = int(str(self.options.msvc))

            runtime = 'MD' if self.options.shared else 'MT'
            if self.settings.build_type == 'Debug':
                runtime += 'd'
            self.info.settings.compiler.runtime = runtime

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
