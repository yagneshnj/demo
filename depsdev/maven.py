import requests
import xml.etree.ElementTree as ET

def query_maven_license(group_artifact: str, version: str):
    group, artifact = group_artifact.split(":")
    group_path = group.replace(".", "/")
    
    # Try DepsDev first
    depsdev_url = f"https://api.deps.dev/v3alpha/systems/maven/packages/{group_artifact}/versions/{version}"
    depsdev_response = requests.get(depsdev_url)
    if depsdev_response.status_code == 200:
        data = depsdev_response.json()
        licenses = data.get("licenses", [])
        if licenses:
            return licenses, "DepsDev"
    
    # Fallback to Maven Central POM
    pom_url = f"https://repo1.maven.org/maven2/{group_path}/{artifact}/{version}/{artifact}-{version}.pom"
    pom_response = requests.get(pom_url)
    if pom_response.status_code == 200:
        try:
            root = ET.fromstring(pom_response.text)
            namespace = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
            licenses = []
            for license_tag in root.findall(".//mvn:licenses/mvn:license/mvn:name", namespace):
                licenses.append(license_tag.text.strip())
            if licenses:
                return licenses, "MavenCentral"
        except Exception as e:
            print(f"Error parsing Maven Central POM XML: {e}")

    # If everything fails
    return [], "Unknown"

