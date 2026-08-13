import os
import glob
import logging
import jpype
import jpype.imports

logger = logging.getLogger(__name__)

def find_jvm_path() -> str:
    """
    Locates libjvm.dylib / libjvm.so / jvm.dll across system, Homebrew, and JAVA_HOME paths.
    """
    # 1. Try default JPype JVM path discovery
    try:
        default_path = jpype.getDefaultJVMPath()
        if default_path and os.path.exists(default_path):
            return default_path
    except Exception:
        pass

    # 2. Check JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates = [
            os.path.join(java_home, "lib", "server", "libjvm.dylib"),
            os.path.join(java_home, "lib", "server", "libjvm.so"),
            os.path.join(java_home, "bin", "server", "jvm.dll"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

    # 3. Known macOS Homebrew & system paths
    homebrew_patterns = [
        "/opt/homebrew/Cellar/openjdk/*/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib",
        "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib",
        "/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home/lib/server/libjvm.dylib",
        "/Library/Java/JavaVirtualMachines/*/Contents/Home/lib/server/libjvm.dylib",
        "/usr/lib/jvm/*/lib/server/libjvm.so",
    ]

    for pattern in homebrew_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    raise RuntimeError(
        "Unable to locate a Java Virtual Machine (libjvm). "
        "Please ensure OpenJDK / Java is installed and JAVA_HOME is set."
    )


def ensure_jvm_started():
    """
    Ensures that JPype JVM is started with MPXJ JAR files in the classpath.
    """
    if jpype.isJVMStarted():
        return

    import mpxj
    mpxj_dir = getattr(mpxj, "mpxj_dir", None)
    if not mpxj_dir:
        mpxj_dir = os.path.join(os.path.dirname(mpxj.__file__), "lib")

    jar_files = glob.glob(os.path.join(mpxj_dir, "*.jar"))
    if not jar_files:
        raise RuntimeError(f"No MPXJ jar files found in {mpxj_dir}")

    classpath_str = os.pathsep.join(jar_files)
    jvm_path = find_jvm_path()

    logger.info(f"Starting JVM using libjvm at '{jvm_path}' with MPXJ classpath.")
    jpype.startJVM(
        jvm_path,
        f"-Djava.class.path={classpath_str}",
        convertStrings=False
    )
