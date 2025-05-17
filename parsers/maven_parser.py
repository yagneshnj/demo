import xml.etree.ElementTree as ET
import re
import requests
from typing import List, Tuple, Dict
import subprocess
import os

MAVEN_CENTRAL_BASE = "https://repo1.maven.org/maven2"
SPRING_REPO_BASE = "https://repo.spring.io/snapshot"


def parse_pom_xml(content: str) -> List[Tuple[str, str]]:
    try:
        root = ET.fromstring(content)
        print("✅ XML parsed successfully.")
    except ET.ParseError:
        print("❌ Error parsing pom.xml")
        return []

    ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

    def extract_properties(root) -> Dict[str, str]:
        props = {}
        props_elem = root.find('mvn:properties', ns)
        if props_elem is not None:
            for prop in props_elem:
                tag = prop.tag.split('}')[-1]
                props[tag] = prop.text.strip() if prop.text else ''

        version_elem = root.find('mvn:version', ns)
        if version_elem is not None:
            props['project.version'] = version_elem.text.strip()

        # Add groupId fallback
        group_id_elem = root.find('mvn:groupId', ns)
        if group_id_elem is not None:
            props['project.groupId'] = group_id_elem.text.strip()
        else:
            parent = root.find('mvn:parent', ns)
            if parent is not None:
                pgid = parent.find('mvn:groupId', ns)
                if pgid is not None:
                    props['project.groupId'] = pgid.text.strip()

        return props

    def fetch_parent_pom(group_id: str, artifact_id: str, version: str) -> Dict[str, str]:
        rel_path = f"{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
        urls = [
            f"{MAVEN_CENTRAL_BASE}/{rel_path}",
            f"{SPRING_REPO_BASE}/{rel_path}"
        ]
        for url in urls:
            print(f"🌐 Trying POM URL: {url}")
            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    print(f"✅ Successfully fetched POM: {url}")
                    parent_root = ET.fromstring(resp.text)
                    return extract_properties(parent_root)
                else:
                    print(f"⚠️ Failed to fetch POM: {url}")
            except Exception as e:
                print(f"⚠️ Exception fetching POM: {url} => {e}")
        return {}

    properties = extract_properties(root)
    print(f"📦 Collected properties: {properties}")

    print("🔁 Resolving parent properties...")
    parent = root.find('mvn:parent', ns)
    if parent is not None:
        gid = parent.find('mvn:groupId', ns)
        aid = parent.find('mvn:artifactId', ns)
        ver = parent.find('mvn:version', ns)
        if gid is not None and aid is not None and ver is not None:
            parent_props = fetch_parent_pom(gid.text.strip(), aid.text.strip(), ver.text.strip())
            properties.update(parent_props)

            # Check for grandparent
            grandparent_props = fetch_parent_pom(
                parent_props.get('project.groupId', gid.text.strip()),
                parent_props.get('artifactId', aid.text.strip()),
                parent_props.get('project.version', ver.text.strip())
            )
            properties.update(grandparent_props)

    def resolve(val: str, depth=0) -> str:
        if not val or depth > 10:
            return "unknown"

        matches = re.findall(r'\$\{(.+?)\}', val)
        for m in matches:
            if m in properties:
                replacement = properties[m]
                # Resolve recursively
                replacement_resolved = resolve(replacement, depth + 1)
                val = val.replace(f"${{{m}}}", replacement_resolved)
            else:
                print(f"❓ Unresolved property: {m}")
                val = val.replace(f"${{{m}}}", "unknown")
        return val

    print("🔍 Processing dependencies...")
    results = []
    dependencies = root.find('mvn:dependencies', ns)
    if dependencies is None:
        print("⚠️ No <dependencies> found.")
        return []

    for dep in dependencies.findall('mvn:dependency', ns):
        groupId = dep.find('mvn:groupId', ns)
        artifactId = dep.find('mvn:artifactId', ns)
        version = dep.find('mvn:version', ns)
        if groupId is None or artifactId is None:
            continue
        ga = f"{resolve(groupId.text.strip())}:{resolve(artifactId.text.strip())}"
        ver = resolve(version.text.strip()) if version is not None else "unknown"
        print(f"✅ Found dependency: {ga}, version: {ver}")
        results.append((ga, ver))

    print(f"✅ Total dependencies found: {len(results)}")
    return results

def parse_pom_xml_via_maven(repo_dir: str) -> List[Tuple[str, str]]:

    try:
        print("🔧 Running Maven to list dependencies...")


        output_file_path = os.path.join(repo_dir, "target", "dependencies.txt")
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        result = subprocess.run([
            "mvn", "dependency:list",
            "-DincludeScope=compile",
            "-Doutput=dependencies",
            "-DoutputAbsoluteArtifactFilename=false",
            f"-DoutputFile={output_file_path}"
        ], cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print("❌ Maven command failed:")
            print(result.stdout)
            print(result.stderr)
            return []

        if not os.path.exists(output_file_path):
            print("⚠️ dependencies.txt not found.")
            return []

        with open(output_file_path) as f:
            lines = f.readlines()

        results = []
        # for line in lines:
        #     line = line.strip()
        #     if ":" in line and not line.startswith("The ") and not line.startswith("---"):
        #         parts = line.split(":")
        #         if len(parts) >= 5:
        #             group = parts[0].strip()
        #             artifact = parts[1].strip()
        #             version = parts[3].strip()
        #             ga = f"{group}:{artifact}"
        #             print(f"✅ Found dependency: {ga}, version: {version}")
        #             results.append((ga, version))
    
        for line in lines:
            line = line.strip()
            if ":" in line and not line.startswith("The ") and not line.startswith("---"):
                parts = line.split(":")
                if len(parts) == 5:
                    group = parts[0]
                    artifact = parts[1]
                    version = parts[4]  # real version
                elif len(parts) == 4:
                    group = parts[0]
                    artifact = parts[1]
                    version = parts[3]
                else:
                    continue
                ga = f"{group}:{artifact}"
                print(f"✅ Found dependency: {ga}, version: {version}")
                results.append((ga, version))

        print(f"✅ Total dependencies found: {len(results)}")
        return results
    
    except Exception as e:
        print(f"❌ Failed to run Maven: {e}")
        return []