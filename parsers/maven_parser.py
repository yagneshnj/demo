import xml.etree.ElementTree as ET
def parse_pom_xml(content: str):
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        print("Error parsing pom.xml")
        return []
    namespace = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
    parent = root.find('mvn:parent', namespace)
    parent_version = parent.find('mvn:version', namespace).text.strip() if parent is not None else None
    dependencies = root.find('mvn:dependencies', namespace)
    results = []
    if dependencies:
        for dep in dependencies.findall('mvn:dependency', namespace):
            groupId = dep.find('mvn:groupId', namespace)
            artifactId = dep.find('mvn:artifactId', namespace)
            version = dep.find('mvn:version', namespace)
            if groupId is not None and artifactId is not None:
                ver = version.text.strip() if version is not None else parent_version or "unknown"
                results.append((f"{groupId.text.strip()}:{artifactId.text.strip()}", ver))
    return results
