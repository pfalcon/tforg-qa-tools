/*##############################################################################

# Copyright (c) 2021, ARM Limited and Contributors. All rights reserved.

#

# SPDX-License-Identifier: BSD-3-Clause

##############################################################################*/
const capitalize = (s) => {
  if (typeof s !== 'string') return ''
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function isValidHttpUrl(str) {
    var regex = /(http|https):\/\/(\w+:{0,1}\w*)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%!\-\/]))?/;
    if(!regex .test(str)) {
        return false;
    } else {
        return true;
    }
}

const slideDown = element => element.style.height = `${element.scrollHeight}px`;

function show(elemId) {
    let elem = document.getElementById(elemId)

    if (elem.style.display == "none") {
        elem.style.display = "block"
        setTimeout(function() {elem.classList.toggle('hide')}, 50)
    } else {
        elem.classList.toggle('hide')
        setTimeout(function() {elem.style.display = "none"}, 750)
    }

}

var counter = 0

class TableReport {

    constructor(data, summary) {
        this.data = data
        this.summary = summary
        this.container = document.createElement("div")
        this.header =  document.createElement("div")
        this.container.classList.add("table-wrap")
        this.table = document.createElement("table")
        this.table.classList.add("styled-table")
        this.container.appendChild(this.header)
        this.container.appendChild(this.table)
        this.generateHeader()
        this.generateTable() // generate the table first
        this.generateTableHead() // then the head
    }

    generateHeader() {
        this.header.innerHTML = "<h2>Test results: " + this.summary["total"] + " tests, " +
                                "<label style='color:green'>" + this.summary["pass"] + " passed,</label> " +
                                "<label style='color:red'>" + this.summary["fail"] +" failed</label></h2>"
    }

    generateTableHead() {
      let table = this.table
      let thead = table.createTHead();
      let row = thead.insertRow();
      for (let key in this.data[0]) {
        let th = document.createElement("th");
        let text = document.createTextNode(capitalize(key));
        th.appendChild(text);
        row.appendChild(th);
      }
    }

    generateTable() {
        let table = this.table
        for (let element of this.data) {
            let row = table.insertRow();
            for (let key in element) {
                let cell = row.insertCell();
                let text = document.createTextNode(element[key]);
                cell.appendChild(text);
            }
        }
    }
}

class Report {

  constructor(reportObj) {
    this.reportObj = reportObj
    this.reportName = Object.keys(this.reportObj)[0]
    this.report = this.reportObj[this.reportName]
    this.testSuites = this.report["test-suites"]
    this.testAssets =  this.report["test-config"]["test-assets"]
    this.metadata = this.report["metadata"]
    this.target = this.report["target"]
    this.testConfig = this.report["test-config"]
    this.testEnvironments = this.report["test-environments"]
    this.testSuitesData = {}
  }

    generateSuitesTables() {
        this.suitesDivs = {}
        var results = []
        var index = 0
        for (const [testSuiteName, testSuite] of Object.entries(this.testSuites)) {
            ++index
            results = []
            var status = "PASS"
            var failCount = 0
            var passCount = 0
            var counter = 0
            var metCols = []
            for (const [testResultName, testResult] of Object.entries(testSuite["test-results"])) {
                results.push({name: testResultName, status: testResult["status"],
                    ...testResult["metadata"]})
                if (testResult["status"] == "FAIL") {
                    status = "FAIL"
                    failCount++
                } else if (testResult["status"] == "PASS") {
                    passCount++
                }
                metCols = Object.keys(testResult["metadata"])
                ++counter
            }
            let summary = {"pass": passCount, "fail": failCount, "total": counter}
            var tableReport = new TableReport(results, summary)
            this.testSuitesData[testSuiteName] = {tableReport: tableReport, metadata: testSuite['metadata']}
        }
    }
}

function link(url) {
    window.open(url, '_blank');
}

function generateItems(obj, container) {
    let i = 0
    let click=""
    for (var [name, value] of Object.entries(obj)) {
        if ((i++ % 3) == 0) {
            divGroup = document.createElement("div")
            divGroup.classList.add("item-parent")
            container.appendChild(divGroup)
        }
        divElem = document.createElement("div")
        divElem.classList.add("item")
        style = ' class=item'
        if (isValidHttpUrl(value))
            style = ' class="link" onclick=link("' + value + '")'
        divElem.innerHTML = "<span style='color:black'>" + name + ": </span>" + "<span" + style +">" + value + "</span>"
        divGroup.appendChild(divElem)
    }
}

function generateBlock(obj, title, expanded, extra) {
    var divBlock = 0
    var divGroup = 0
    var divElem = 0
    var divData = 0

    if (expanded === undefined)
        expanded = true
    let id = title.replace(/\s+/g, '-') + counter++
    let checked = expanded ? "checked" : ""
    divBlock = document.createElement("div")
    divBlock.classList.add("block-report")
    let divTitle = document.createElement("div")
    divTitle.innerHTML = '<label>' + title + '</div>' +
                        '<label class="switch"><input ' +
                        '" type="checkbox" ' + checked + ' onclick=' +
                        "show('data-" + id + "')>" +
                        '<span class="slider"></span></label>'
    divBlock.appendChild(divTitle)
    if (obj.tagName == 'DIV')
        divData = obj
    else
        divData = document.createElement("div")
    divData.id = "data-" + id
    divData.classList.add("box")
    divBlock.setAttribute('data-items-container', divData.id)
    if (expanded == false) {
        divData.style.display = 'none'
        divData.classList.add("hide")
        }

    divBlock.appendChild(divData)
    generateItems(obj, divData)
    if (!(extra === undefined))
        divData.appendChild(extra)
    return divBlock
}

function generateReport(containerName, yamlString) {
    const jsObject = JSON.parse(yamlString)
    const report = new Report(jsObject)
    document.getElementById("report-name").innerHTML = report.reportName
    var divContent = document.getElementById("report-content")

    var metadata = generateBlock(report.metadata, "Metadata", false)
    divContent.appendChild(metadata)

    divContent.appendChild(generateBlock(report.target, "Target", false))

    var div = document.createElement("div")
    divAssets = generateBlock(div, "Test assets", false)
    for (const [name, data] of Object.entries(report.testConfig['test-assets'])) {
        var divAsset = generateBlock(data, name, false)
        div.appendChild(divAsset)
    }

    divConfig = generateBlock(divAssets, "Test configuration", false)
    divContent.appendChild(divConfig)

    div = document.createElement("div")
    divEnvs = generateBlock(div, "Test environments", false)
    for (const [name, data] of Object.entries(report.testEnvironments)) {
        var divEnv = generateBlock(data, name, false)
        div.appendChild(divEnv)
    }
    divContent.appendChild(divEnvs)

    div = document.createElement("div")
    divSuites = generateBlock(div, "Test suites")
    report.generateSuitesTables()
    var visible = true
    for (const [name, suiteData] of Object.entries(report.testSuitesData)) {
        var divSuite = generateBlock(suiteData['metadata'], name, visible, suiteData['tableReport'].container)
        div.appendChild(divSuite)
        if (visible)
            visible = false
    }

    divContent.appendChild(divSuites)
    return report
}
