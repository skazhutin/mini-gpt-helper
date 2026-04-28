#include <Python.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void die(const char *message) {
    fprintf(stderr, "%s\n", message);
    exit(1);
}

static void dirname_inplace(char *path) {
    char *slash = strrchr(path, '/');
    if (slash == NULL) {
        return;
    }
    *slash = '\0';
}

static void read_line(const char *path, char *buffer, size_t size) {
    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        perror(path);
        exit(1);
    }

    if (fgets(buffer, (int)size, fp) == NULL) {
        fclose(fp);
        die("Failed to read launcher metadata");
    }
    fclose(fp);

    size_t len = strlen(buffer);
    while (len > 0 && (buffer[len - 1] == '\n' || buffer[len - 1] == '\r')) {
        buffer[len - 1] = '\0';
        len--;
    }
}

static void set_env_path(const char *key, const char *value) {
    if (setenv(key, value, 1) != 0) {
        perror(key);
        exit(1);
    }
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    char exe_path[PATH_MAX];
    uint32_t exe_size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &exe_size) != 0) {
        die("Executable path buffer too small");
    }

    char exe_dir[PATH_MAX];
    strncpy(exe_dir, exe_path, sizeof(exe_dir) - 1);
    exe_dir[sizeof(exe_dir) - 1] = '\0';
    dirname_inplace(exe_dir);

    char bundle_contents[PATH_MAX];
    strncpy(bundle_contents, exe_dir, sizeof(bundle_contents) - 1);
    bundle_contents[sizeof(bundle_contents) - 1] = '\0';
    dirname_inplace(bundle_contents);

    char resources_dir[PATH_MAX];
    snprintf(resources_dir, sizeof(resources_dir), "%s/Resources", bundle_contents);

    char repo_root_file[PATH_MAX];
    snprintf(repo_root_file, sizeof(repo_root_file), "%s/repo_root.txt", resources_dir);

    char repo_root[PATH_MAX];
    read_line(repo_root_file, repo_root, sizeof(repo_root));

    if (chdir(repo_root) != 0) {
        perror(repo_root);
        return 1;
    }

    char python_path[PATH_MAX * 2];
    snprintf(
        python_path,
        sizeof(python_path),
        "%s:%s/.venv/lib/python3.12/site-packages",
        repo_root,
        repo_root
    );

    set_env_path("PYTHONPATH", python_path);
    set_env_path("PYTHONEXECUTABLE", exe_path);

    char *py_argv[] = {exe_path, "main.py", NULL};
    return Py_BytesMain(2, py_argv);
}
