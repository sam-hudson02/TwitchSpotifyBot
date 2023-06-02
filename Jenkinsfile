pipeline {
  agent {
    node {
      label 'pi'
    }
    
    }
    environment {
        DOCKER_CREDS = credentials('docker_hub')
    }
    stages {
        stage('pull code') {
            steps {
                git(url: 'https://github.com/sam-hudson02/TwitchSpotifyBot', branch: 'main', credentialsId: 'personal_github')
            }
        }
        stage('build docker image') {
            steps {
                script {
                    // increment the version number
                    def version = env.TSB_VERSION
                    version = version.toInteger() + 1
                    env.TSB_VERSION = version
                    def versionString = version.toString()
                  
                    // add zero to start of version if needed
                    if (versionString.length() == 2) {
                        versionString = "0" + versionString
                    }

                    // add . between each number
                    def versionStringFormatted = versionString.split('').join('.')

                    // build docker image with version and latest tags
                    sh "docker build -t samhudson02/sbotify:${versionStringFormatted} -t samhudson02/sbotify:latest ."
                    // login to docker hub
                    sh 'docker login -u $DOCKER_CREDS_USR -p $DOCKER_CREDS_PSW'
                    // push docker image to docker hub
                    sh "docker push samhudson02/sbotify:${versionStringFormatted}"

                    def branch = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
                    if (branch == "main") {
                        sh "docker push samhudson02/sbotify:latest"
                    }
                }
            }
        }
    }
    post {
        success {
            script {
                def gitCommit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                def gitAuthor = sh(returnStdout: true, script: 'git --no-pager show -s --format=%an').trim()
                def dateTime = sh(returnStdout: true, script: 'date +%d-%m-%Y_%H:%M:%S').trim()
                // remove the 'and counting' from the duration string
                def buildTime = currentBuild.durationString.split('and')[0].trim()
                def commitURL = "https://github.com/sam-hudson02/TwitchSpotifyBot/commit/" + gitCommit
                def commitTitle = sh(returnStdout: true, script: 'git log -1 --pretty=%B').trim()

                def payload = [
                    "build_id": env.BUILD_ID,
                    "build_name": "TwitchSpotifyBot",
                    "build_url": env.BUILD_URL,
                    "build_date": dateTime,
                    "commit_author": gitAuthor,
                    "commit_title": commitTitle,
                    "commit_url": commitURL,
                    "build_result": "SUCCESS",
                    "build_duration": buildTime
                ]

                def payloadString = payload.collect{ k,v -> "\"${k}\":\"${v}\"" }.join(',')
                def payloadJson = "{${payloadString}}"
                sh "curl -d '${payloadJson}' -H 'Content-Type: application/json' http://192.168.3.101:5005/build-notify"
            }
        }
        failure {
            script {
                def gitCommit = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                def gitAuthor = sh(returnStdout: true, script: 'git --no-pager show -s --format=%an').trim()
                def dateTime = sh(returnStdout: true, script: 'date +%d-%m-%Y_%H:%M:%S').trim()
                // remove the 'and counting' from the duration string
                def buildTime = currentBuild.durationString.split('and')[0].trim()
                def commitURL = "https://github.com/sam-hudson02/TwitchSpotifyBot/commit/" + gitCommit
                def commitTitle = sh(returnStdout: true, script: 'git log -1 --pretty=%B').trim()

                def payload = [
                    "build_id": env.BUILD_ID,
                    "build_name": "TwitchSpotifyBot",
                    "build_url": env.BUILD_URL,
                    "build_date": dateTime,
                    "commit_author": gitAuthor,
                    "commit_title": commitTitle,
                    "commit_url": commitURL,
                    "build_result": "FAILURE",
                    "build_duration": buildTime
                ]

                def payloadString = payload.collect{ k,v -> "\"${k}\":\"${v}\"" }.join(',')
                def payloadJson = "{${payloadString}}"
                sh "curl -d '${payloadJson}' -H 'Content-Type: application/json' http://192.168.3.101:5005/build-notify"
            }
        }
    }
    tools {
        nodejs 'nodejs'
    }
}
