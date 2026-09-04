from __future__ import annotations

import unittest
from pathlib import Path

import yaml


STACK_ROOT = Path(__file__).resolve().parents[1]


class StackWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = yaml.safe_load((STACK_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        cls.services = cls.compose["services"]

    def test_profiles_keep_runtime_core_minimal_and_optionals_independent(self):
        shared_profiles = set(self.services["wechat-runtime"]["profiles"])
        self.assertEqual(
            shared_profiles,
            {"implementation", "core", "console", "agent", "efb"},
        )
        self.assertEqual(set(self.services["wechat-core"]["profiles"]), shared_profiles)
        self.assertEqual(self.services["wechat-console"]["profiles"], ["console"])
        self.assertEqual(self.services["wechat-agent"]["profiles"], ["agent"])
        self.assertEqual(self.services["efb-multi"]["profiles"], ["efb"])
        self.assertEqual(self.services["mock-core"]["profiles"], ["mock"])

    def test_core_waits_for_bootstrapped_runtime_and_shares_required_namespaces(self):
        core = self.services["wechat-core"]
        runtime = self.services["wechat-runtime"]
        self.assertEqual(core["pid"], "service:wechat-runtime")
        self.assertEqual(core["depends_on"]["wechat-runtime"]["condition"], "service_healthy")
        self.assertIn("runtime-config:/app/config:ro", core["volumes"])
        self.assertIn("runtime-state:/run/wechat-runtime", core["volumes"])
        self.assertIn("runtime-x11:/tmp/.X11-unix", core["volumes"])
        self.assertIn("runtime-state:/run/wechat-runtime", runtime["volumes"])
        self.assertIn("runtime-x11:/tmp/.X11-unix", runtime["volumes"])
        runtime_health = " ".join(runtime["healthcheck"]["test"])
        self.assertIn("bootstrap.ready", runtime_health)
        self.assertIn("control.sock", runtime_health)
        self.assertIn("healthz", runtime_health)
        self.assertIn("WECHAT_DESKTOP_GATEWAY_PORT", runtime_health)
        self.assertIn(
            "WECHAT_RUNTIME_CONTROL_SOCKET=/run/wechat-runtime/control.sock",
            runtime["environment"],
        )
        self.assertIn("WECHAT_GUI_LEASE_DIR=/run/wechat-runtime/locks", runtime["environment"])
        self.assertIn(
            "WECHAT_RUNTIME_CONTROL_SOCKET=/run/wechat-runtime/control.sock",
            core["environment"],
        )
        self.assertIn("WECHAT_GUI_LEASE_DIR=/run/wechat-runtime/locks", core["environment"])
        self.assertIn("--runtime-control-socket", core["command"])
        self.assertIn("/run/wechat-runtime/control.sock", core["command"])
        self.assertIn("--registry-reload-interval", core["command"])

    def test_runtime_control_uses_current_linuxserver_custom_service_hook(self):
        runtime_dockerfile = (STACK_ROOT.parent / "work" / "runtime" / "Dockerfile").read_text(encoding="utf-8")
        service_script = STACK_ROOT.parent / "work" / "runtime" / "root" / "custom-services.d" / "wechat-runtime-control"
        gateway_script = STACK_ROOT.parent / "work" / "runtime" / "root" / "custom-services.d" / "wechat-desktop-gateway"
        self.assertTrue(service_script.is_file())
        self.assertTrue(gateway_script.is_file())
        self.assertIn("/custom-services.d/wechat-runtime-control", runtime_dockerfile)
        self.assertIn("/custom-services.d/wechat-desktop-gateway", runtime_dockerfile)
        self.assertIn("aiohttp==3.12.15", runtime_dockerfile)
        self.assertNotIn("/etc/services.d/wechat-runtime-control", runtime_dockerfile)

    def test_agent_desktop_uses_gateway_instead_of_host_published_child_port(self):
        runtime = self.services["wechat-runtime"]
        environment = [str(item) for item in runtime.get("environment", [])]
        ports = [str(item) for item in runtime.get("ports", [])]
        runtime_source = (
            STACK_ROOT.parent
            / "work"
            / "runtime"
            / "root"
            / "scripts"
            / "wechat"
            / "agent_wechat_runtime.py"
        ).read_text(encoding="utf-8")
        gateway_source = (
            STACK_ROOT.parent
            / "work"
            / "runtime"
            / "root"
            / "scripts"
            / "wechat"
            / "desktop_gateway.py"
        ).read_text(encoding="utf-8")

        self.assertFalse(any("AGENT_WECHAT_DESKTOP_BIND" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_PORT=" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_MAX_WS_FRAME_MB=" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_MAX_HTTP_MB=" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME=" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_PUBLIC_HOST=" in item for item in environment))
        self.assertTrue(any("WECHAT_DESKTOP_GATEWAY_PUBLIC_PORT=" in item for item in environment))
        self.assertTrue(any("WECHAT_SELKIES_ATTACH_ENABLED=" in item for item in environment))
        self.assertTrue(any("17892" in item for item in ports))
        self.assertFalse(any(":6174" in item or "6174:" in item for item in ports))
        self.assertFalse(any(":8081" in item or "8081:" in item for item in ports))
        self.assertNotIn('"PortBindings"', runtime_source)
        self.assertIn("SELKIES_ATTACH_COMMAND", runtime_source)
        self.assertIn('"IpcMode": f"container:{parent_container_id}"', runtime_source)
        self.assertIn('"NetworkMode": f"container:{parent_container_id}"', runtime_source)
        self.assertIn("SELKIES_FILE_TRANSFERS=upload,download", runtime_source)
        self.assertIn("SELKIES_COMMAND_ENABLED=false|locked", runtime_source)
        self.assertIn("access_log=None", gateway_source)
        self.assertIn("WSMsgType.BINARY", gateway_source)
        self.assertIn("Authorization", gateway_source)
        self.assertIn("selkies_upstream_url", gateway_source)

    def test_runtime_manager_base_selkies_clipboard_is_hard_disabled(self):
        runtime = self.services["wechat-runtime"]
        environment = set(str(item) for item in runtime.get("environment", []))
        expected = {
            "SELKIES_CLIPBOARD_ENABLED=false|locked",
            "SELKIES_CLIPBOARD_IN_ENABLED=false|locked",
            "SELKIES_CLIPBOARD_OUT_ENABLED=false|locked",
            "SELKIES_ENABLE_BINARY_CLIPBOARD=false|locked",
            "SELKIES_UI_SIDEBAR_SHOW_CLIPBOARD=false|locked",
        }
        self.assertTrue(expected.issubset(environment))
        self.assertEqual(runtime.get("pids_limit"), 200)

        # The production overlay uses Docker Compose's ``!reset`` tag, which
        # PyYAML's SafeLoader intentionally does not understand.  Keep this
        # assertion textual and narrowly scoped to the explicit P0 settings.
        production_text = (
            STACK_ROOT.parent / "release" / "docker-compose.production.yml"
        ).read_text(encoding="utf-8")
        for setting in expected:
            self.assertIn(f"- {setting}", production_text)
        self.assertIn("pids_limit: 200", production_text)

    def test_optional_services_depend_only_on_healthy_core(self):
        for service_name in ("efb-multi", "wechat-console", "wechat-agent"):
            depends = self.services[service_name]["depends_on"]
            self.assertEqual(set(depends), {"wechat-core"})
            self.assertEqual(depends["wechat-core"]["condition"], "service_healthy")

    def test_all_stack_services_have_explicit_pids_limits(self):
        for service_name, service in self.services.items():
            self.assertIsInstance(
                service.get("pids_limit"),
                int,
                f"{service_name} must have an explicit pids_limit",
            )
            self.assertGreater(service["pids_limit"], 0)

        production_text = (
            STACK_ROOT.parent / "release" / "docker-compose.production.yml"
        ).read_text(encoding="utf-8")
        self.assertRegex(production_text, r"(?s)efb-multi:.*?pids_limit:\s*100")

    def test_console_and_agent_state_are_persistent(self):
        console = self.services["wechat-console"]
        agent = self.services["wechat-agent"]
        self.assertIn("console-data:/data/wechat-console", console["volumes"])
        self.assertIn("agent-data:/data", agent["volumes"])
        self.assertIn("WECHAT_CORE_URL=http://wechat-core:8080", console["environment"])
        self.assertIn("WECHAT_CORE_URL=http://wechat-core:8080", agent["environment"])
        self.assertIn(
            "WECHAT_AGENT_LEGACY_RUNTIME_DIR=/data/legacy-agent-console",
            agent["environment"],
        )

    def test_sensitive_control_ports_default_to_loopback(self):
        self.assertIn("127.0.0.1", self.services["wechat-core"]["ports"][0])
        self.assertIn("127.0.0.1", self.services["wechat-console"]["ports"][0])
        self.assertIn("127.0.0.1", self.services["wechat-agent"]["ports"][0])

    def test_only_runtime_manager_has_docker_engine_socket(self):
        socket_mount = "/var/run/docker.sock:/var/run/docker.sock"
        runtime_volumes = self.services["wechat-runtime"].get("volumes", [])
        self.assertIn(socket_mount, runtime_volumes)
        for service_name, service in self.services.items():
            if service_name == "wechat-runtime":
                continue
            volumes = [str(item) for item in service.get("volumes", [])]
            self.assertFalse(
                any("/var/run/docker.sock" in item for item in volumes),
                f"{service_name} must not receive Docker Engine access",
            )


if __name__ == "__main__":
    unittest.main()
