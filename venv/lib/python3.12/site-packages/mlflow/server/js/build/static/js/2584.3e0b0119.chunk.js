"use strict";(self.webpackChunk_mlflow_mlflow=self.webpackChunk_mlflow_mlflow||[]).push([[2584],{16144:function(e,r,t){t.d(r,{f:function(){return n.f}});var n=t(64226)},17763:function(e,r,t){t.d(r,{P:function(){return a}});t(46709);var n=t(16144),o=t(73408);const a=({value:e})=>{const r=new Date(Number(e));return isNaN(r)?null:(0,o.Y)(n.f,{date:r})}},19816:function(e,r,t){t.d(r,{u:function(){return p},g:function(){return g}});var n=t(76118),o=t(46709),a=t(56530),i=t(5690),l=t(99213),s=t(11522);var d=t(99002),u=t(31655),c=t(27206);const v=({queryResult:e,runUuid:r})=>{const{registeredModels:t}=(0,a.d4)(({entities:e})=>({registeredModels:e.modelVersionsByRunUuid[r]}));if((0,u._O)()){const r=[];var n,o;if(null!==e&&void 0!==e&&e.data&&"modelVersions"in e.data)null===(n=e.data)||void 0===n||null===(o=n.modelVersions)||void 0===o||o.forEach(e=>{r.push({displayedName:e.name,version:e.version,link:e.name&&e.version?c.fM.getModelVersionPageRoute(e.name,e.version):"",status:e.status,source:e.source})});return r}return t?t.map(e=>{const r=e.name,t=c.fM.getModelVersionPageRoute(r,e.version);return{displayedName:e.name,version:e.version,link:t,status:e.status,source:e.source}}):[]},m=e=>(0,n.keyBy)(e,"key"),p=e=>null===e||void 0===e?void 0:e.map(e=>{var r,t,o,a,i,l,s,d,u,c,v,m,p,g;return{dataset:{digest:null!==(r=null===(t=e.dataset)||void 0===t?void 0:t.digest)&&void 0!==r?r:"",name:null!==(o=null===(a=e.dataset)||void 0===a?void 0:a.name)&&void 0!==o?o:"",profile:null!==(i=null===(l=e.dataset)||void 0===l?void 0:l.profile)&&void 0!==i?i:"",schema:null!==(s=null===(d=e.dataset)||void 0===d?void 0:d.schema)&&void 0!==s?s:"",source:null!==(u=null===(c=e.dataset)||void 0===c?void 0:c.source)&&void 0!==u?u:"",sourceType:null!==(v=null===(m=e.dataset)||void 0===m?void 0:m.sourceType)&&void 0!==v?v:""},tags:null!==(p=null===(g=e.tags)||void 0===g?void 0:g.map(e=>{var r,t;return{key:null!==(r=e.key)&&void 0!==r?r:"",value:null!==(t=e.value)&&void 0!==t?t:""}}).filter(e=>!(0,n.isEmpty)(e.key)))&&void 0!==p?p:[]}}),g=({runUuid:e,experimentId:r})=>{var t,c,g,f,h,E;const y=(0,u.wD)(),D=(0,a.wA)(),k=!0;if(y){var I,_,w,M,A,R;const r=(()=>(0,d.t)({runUuid:e}))();(0,o.useEffect)(()=>{(0,u._O)()||D((0,l.hY)({run_id:e}))},[D,e,k]);const{latestMetrics:t,tags:a,params:i,datasets:s}=(0,o.useMemo)(()=>{var e,t,o,a,i,l,s,d,u,c,v,g;return{latestMetrics:(0,n.pickBy)(m((g=null!==(e=null===(t=r.data)||void 0===t||null===(o=t.data)||void 0===o?void 0:o.metrics)&&void 0!==e?e:[],g.filter(({key:e,value:r,step:t,timestamp:n})=>null!==e&&null!==r&&null!==t&&null!==n).map(({key:e,value:r,step:t,timestamp:n})=>({key:e,value:r,step:Number(t),timestamp:Number(n)})))),e=>e.key.trim().length>0),tags:(0,n.pickBy)(m(null!==(a=null===(i=r.data)||void 0===i||null===(l=i.data)||void 0===l?void 0:l.tags)&&void 0!==a?a:[]),e=>e.key.trim().length>0),params:(0,n.pickBy)(m(null!==(s=null===(d=r.data)||void 0===d||null===(u=d.data)||void 0===u?void 0:u.params)&&void 0!==s?s:[]),e=>e.key.trim().length>0),datasets:p(null===(c=r.data)||void 0===c||null===(v=c.inputs)||void 0===v?void 0:v.datasetInputs)}},[r.data]),c=v({runUuid:e,queryResult:r});return{runInfo:null!==(I=null===(_=r.data)||void 0===_?void 0:_.info)&&void 0!==I?I:void 0,experiment:null!==(w=null===(M=r.data)||void 0===M?void 0:M.experiment)&&void 0!==w?w:void 0,loading:r.loading,error:r.apolloError,apiError:r.apiError,refetchRun:r.refetchRun,runInputs:null===(A=r.data)||void 0===A?void 0:A.inputs,runOutputs:null===(R=r.data)||void 0===R?void 0:R.outputs,registeredModelVersionSummaries:c,datasets:s,latestMetrics:t,tags:a,params:i}}const T=((e,r,t=!0)=>{const[d,u]=(0,o.useState)(""),[c,v]=(0,o.useState)(""),m=(0,a.wA)(),{runInfo:p,tags:g,latestMetrics:f,experiment:h,params:E,datasets:y}=(0,a.d4)(t=>({runInfo:t.entities.runInfosByUuid[e],tags:(0,n.pickBy)(t.entities.tagsByRunUuid[e],e=>e.key.trim().length>0),latestMetrics:(0,n.pickBy)(t.entities.latestMetricsByRunUuid[e],e=>e.key.trim().length>0),params:(0,n.pickBy)(t.entities.paramsByRunUuid[e],e=>e.key.trim().length>0),experiment:t.entities.experimentsById[r],datasets:t.entities.runDatasetsByUuid[e]})),D=(0,o.useCallback)(()=>{const r=(0,i.aO)(e);return u(r.meta.id),m(r)},[m,e]),k=(0,o.useCallback)(()=>{const e=(0,i.yc)(r);return v(e.meta.id),m(e)},[m,r]),I=(0,o.useCallback)(()=>{t&&m((0,l.hY)({run_id:e}))},[m,e,t]);(0,o.useEffect)(()=>{p||D().catch(e=>s.A.logErrorAndNotifyUser(e)),I()},[p,D,I]),(0,o.useEffect)(()=>{h||k().catch(e=>s.A.logErrorAndNotifyUser(e))},[h,k]);const{loading:_,error:w}=(0,a.d4)(e=>{var r,t,n,o;return{loading:!d||Boolean(null===(r=e.apis)||void 0===r||null===(t=r[d])||void 0===t?void 0:t.active),error:null===(n=e.apis)||void 0===n||null===(o=n[d])||void 0===o?void 0:o.error}}),{loading:M,error:A}=(0,a.d4)(e=>{var r,t,n,o;return{loading:!d||Boolean(null===(r=e.apis)||void 0===r||null===(t=r[c])||void 0===t?void 0:t.active),error:null===(n=e.apis)||void 0===n||null===(o=n[c])||void 0===o?void 0:o.error}});return{loading:_||M,data:{runInfo:p,tags:g,params:E,latestMetrics:f,experiment:h,datasets:y},refetchRun:D,errors:{runFetchError:w,experimentFetchError:A}}})(e,r,k),U=T.errors.runFetchError||T.errors.experimentFetchError,x=v({runUuid:e});return{runInfo:null===(t=T.data)||void 0===t?void 0:t.runInfo,latestMetrics:null===(c=T.data)||void 0===c?void 0:c.latestMetrics,tags:null===(g=T.data)||void 0===g?void 0:g.tags,experiment:null===(f=T.data)||void 0===f?void 0:f.experiment,params:null===(h=T.data)||void 0===h?void 0:h.params,datasets:null===(E=T.data)||void 0===E?void 0:E.datasets,loading:T.loading,error:U,runFetchError:T.errors.runFetchError,experimentFetchError:T.errors.experimentFetchError,refetchRun:T.refetchRun,registeredModelVersionSummaries:x}}},29774:function(e,r,t){t.d(r,{Au:function(){return l},tF:function(){return s}});var n=t(46709),o=t(36476),a=t(73408);const i=(0,n.createContext)({currentUserActionError:null,handleError:()=>{},handlePromise:()=>{},clearUserActionError:()=>{}}),l=({children:e,errorFilter:r})=>{const[t,l]=(0,n.useState)(null),s=(0,n.useCallback)((e,t)=>{if(null===r||void 0===r||!r(e)){const r=(0,o.a$)(e);l(r),t&&t(r)}},[l,r]),d=(0,n.useCallback)(e=>{e.catch(e=>{s(e)})},[s]),u=(0,n.useCallback)(()=>{l(null)},[l]);return(0,a.Y)(i.Provider,{value:(0,n.useMemo)(()=>({currentUserActionError:t,handleError:s,handlePromise:d,clearUserActionError:u}),[u,t,s,d]),children:e})},s=()=>{const{currentUserActionError:e,handleError:r,handlePromise:t,clearUserActionError:o}=(0,n.useContext)(i),a=(0,n.useCallback)((e,t,n)=>{r(t,n)},[r]);return(0,n.useMemo)(()=>({currentUserActionError:e,handleError:r,handleErrorWithEvent:a,handlePromise:t,clearUserActionError:o}),[o,r,t,e,a])}},75173:function(e,r,t){t.d(r,{Xs:function(){return p},s7:function(){return g}});var n=t(46709),o=t(48292),a=t(99002),i=t(19816),l=t(76118),s=t(36476),d=t(24523),u=t(40724),c=t(73408);class v extends s.ZR{constructor(...e){super(...e),this.errorLogType=s.ZQ.UnexpectedSystemStateError,this.errorName=s.UW.DatasetRunNotFoundError,this.isUserError=!0,this.displayMessage=(0,c.Y)(u.A,{id:"vwDBPr",defaultMessage:"The run containing the dataset could not be found."})}}const m=(0,n.createContext)({onDatasetClicked:()=>Promise.resolve()}),p=({children:e})=>{const[r,t]=(0,n.useState)(!1),[s,u]=(0,n.useState)(),[p]=(0,a.T)(),g=(0,n.useRef)(null),f=(0,n.useCallback)(async e=>new Promise((r,n)=>{var o;return null===(o=g.current)||void 0===o||o.call(g),p({onError:n,onCompleted(o){var a,s,c,m,p,f,h,E,y,D,k;if(null!==(a=o.mlflowGetRun)&&void 0!==a&&a.apiError){const e=o.mlflowGetRun.apiError.code===d.tG.RESOURCE_DOES_NOT_EXIST?new v:o.mlflowGetRun.apiError;return void n(e)}const I=(0,i.u)(null===(s=o.mlflowGetRun)||void 0===s||null===(c=s.run)||void 0===c||null===(m=c.inputs)||void 0===m?void 0:m.datasetInputs);if(!I||null===(p=o.mlflowGetRun)||void 0===p||null===(f=p.run)||void 0===f||!f.info)return void r();const _=null===I||void 0===I?void 0:I.find(r=>{var t;return(null===(t=r.dataset)||void 0===t?void 0:t.digest)===e.datasetDigest&&r.dataset.name===e.datasetName});if(!_)return void r();const{info:w,data:M}=o.mlflowGetRun.run,A=(0,l.keyBy)(null!==(h=null===M||void 0===M||null===(E=M.tags)||void 0===E?void 0:E.filter(e=>e.key&&e.value))&&void 0!==h?h:[],"key");t(!0),u({datasetWithTags:{dataset:_.dataset,tags:_.tags},runData:{datasets:I,runUuid:null!==(y=w.runUuid)&&void 0!==y?y:"",experimentId:null!==(D=w.experimentId)&&void 0!==D?D:"",runName:null!==(k=w.runName)&&void 0!==k?k:"",tags:A}}),r(),g.current=null},variables:{data:{runId:e.runId}}})}),[p]),h=(0,n.useMemo)(()=>({onDatasetClicked:f}),[f]);return(0,c.FD)(m.Provider,{value:h,children:[e,s&&(0,c.Y)(o.O,{isOpen:r,selectedDatasetWithRun:s,setIsOpen:t,setSelectedDatasetWithRun:u})]})},g=()=>(0,n.useContext)(m)},79557:function(e,r,t){t.d(r,{J:function(){return f}});var n=t(68248),o=t(82716),a=t(27757),i=t(79081),l=t(11522),s=t(44105),d=t(91701),u=t(42762),c=t(46709),v=t(91105),m=t(73408);var p={name:"1wcfv52",styles:"margin-right:0"},g={name:"1a7v7i3",styles:"margin-right:0;&>div{padding-right:0;}"};const f=({loggedModel:e,displayDetails:r,className:t})=>{var f,h,E,y;const[D]=(0,v.ok)(),k=(0,c.useMemo)(()=>{var r,t,n;return null!==(r=null===e||void 0===e||null===(t=e.info)||void 0===t||null===(n=t.tags)||void 0===n?void 0:n.reduce((e,r)=>r.key?(e[r.key]=r,e):e,{}))&&void 0!==r?r:{}},[null===e||void 0===e||null===(f=e.info)||void 0===f?void 0:f.tags]),I=null===k||void 0===k||null===(h=k[s.xd])||void 0===h?void 0:h.value,_=null===k||void 0===k||null===(E=k[l.A.gitCommitTag])||void 0===E?void 0:E.value,w=(0,c.useMemo)(()=>{try{return l.A.renderSource(k,D.toString(),void 0,I)}catch(e){return}},[k,D,I]),M=null===(y=k[l.A.sourceTypeTag])||void 0===y?void 0:y.value,{theme:A}=(0,a.u)();return w?(0,m.FD)("div",{css:(0,n.AH)({display:"flex",alignItems:"center",gap:A.spacing.sm,paddingTop:A.spacing.sm,paddingBottom:A.spacing.sm,flexWrap:r?"wrap":void 0},""),className:t,children:[M&&(0,m.Y)(u.m,{sourceType:M,css:(0,n.AH)({color:A.colors.actionPrimaryBackgroundDefault},"")}),w," ",r&&I&&(0,m.Y)(i.T,{componentId:"mlflow.logged_model.details.source.branch_tooltip",content:I,children:(0,m.Y)(o.Tag,{componentId:"mlflow.logged_model.details.source.branch",css:p,children:(0,m.FD)("div",{css:(0,n.AH)({display:"flex",gap:A.spacing.xs,whiteSpace:"nowrap"},""),children:[(0,m.Y)(o.BranchIcon,{})," ",I]})})}),r&&_&&(0,m.FD)(a.aw.Root,{componentId:"mlflow.logged_model.details.source.commit_hash_popover",children:[(0,m.Y)(a.aw.Trigger,{asChild:!0,children:(0,m.Y)(o.Tag,{componentId:"mlflow.logged_model.details.source.commit_hash",css:g,children:(0,m.FD)("div",{css:(0,n.AH)({display:"flex",gap:A.spacing.xs,whiteSpace:"nowrap",alignContent:"center"},""),children:[(0,m.Y)(o.GitCommitIcon,{}),_.slice(0,7)]})})}),(0,m.FD)(a.aw.Content,{align:"start",children:[(0,m.Y)(a.aw.Arrow,{}),(0,m.FD)("div",{css:(0,n.AH)({display:"flex",gap:A.spacing.xs,alignItems:"center"},""),children:[_,(0,m.Y)(d.i,{showLabel:!1,size:"small",type:"tertiary",copyText:_,icon:(0,m.Y)(o.CopyIcon,{})})]})]})]})]}):(0,m.Y)(a.T.Hint,{children:"\u2014"})}},86134:function(e,r,t){t.d(r,{a:function(){return c}});var n=t(68248),o=t(82716),a=t(27757),i=t(66916),l=t(40724),s=t(67069),d=t(73408);const u=({status:e})=>e===s.Fq.LOGGED_MODEL_READY?(0,d.Y)(o.CheckCircleIcon,{color:"success"}):e===s.Fq.LOGGED_MODEL_UPLOAD_FAILED?(0,d.Y)(o.XCircleIcon,{color:"danger"}):e===s.Fq.LOGGED_MODEL_PENDING?(0,d.Y)(i.C,{color:"warning"}):null,c=({data:e})=>{var r,t;const{theme:i}=(0,a.u)(),c=null!==(r=null===(t=e.info)||void 0===t?void 0:t.status)&&void 0!==r?r:s.Fq.LOGGED_MODEL_STATUS_UNSPECIFIED;return c===s.Fq.LOGGED_MODEL_STATUS_UNSPECIFIED?null:(0,d.FD)(o.Tag,{componentId:"mlflow.logged_model.status",css:(0,n.AH)({backgroundColor:c===s.Fq.LOGGED_MODEL_READY?i.isDarkMode?i.colors.green800:i.colors.green100:c===s.Fq.LOGGED_MODEL_UPLOAD_FAILED?i.isDarkMode?i.colors.red800:i.colors.red100:c===s.Fq.LOGGED_MODEL_PENDING?i.isDarkMode?i.colors.yellow800:i.colors.yellow100:void 0},""),children:[c&&(0,d.Y)(u,{status:c})," ",(0,d.Y)(a.T.Text,{css:(0,n.AH)({marginLeft:i.spacing.sm},""),children:c===s.Fq.LOGGED_MODEL_READY?(0,d.Y)(a.T.Text,{color:"success",children:(0,d.Y)(l.A,{id:"Rs+SVS",defaultMessage:"Ready"})}):c===s.Fq.LOGGED_MODEL_UPLOAD_FAILED?(0,d.Y)(a.T.Text,{color:"error",children:(0,d.Y)(l.A,{id:"e6reUn",defaultMessage:"Failed"})}):c===s.Fq.LOGGED_MODEL_PENDING?(0,d.Y)(a.T.Text,{color:"warning",children:(0,d.Y)(l.A,{id:"jo4LfR",defaultMessage:"Pending"})}):c})]})}},97587:function(e,r,t){t.d(r,{f:function(){return u}});var n=t(68248),o=t(82716),a=t(27757),i=t(46709),l=t(75173),s=t(29774),d=t(73408);const u=({datasetName:e,datasetDigest:r,runId:t})=>{const{theme:u}=(0,a.u)(),[c,v]=(0,i.useState)(!1),{onDatasetClicked:m}=(0,l.s7)(),{handleError:p}=(0,s.tF)();return(0,d.FD)(a.B,{type:"link",icon:c?(0,d.Y)(a.S,{size:"small",css:(0,n.AH)({marginRight:u.spacing.sm},"")}):(0,d.Y)(o.TableIcon,{}),componentId:"mlflow.logged_model.dataset",onClick:()=>((e,r,t)=>{t&&(v(!0),null===m||void 0===m||m({datasetName:e,datasetDigest:r,runId:t}).catch(e=>{p(e)}).finally(()=>v(!1)))})(e,r,t),children:[e," (#",r,")"]},[e,r].join("."))}},99002:function(e,r,t){t.d(r,{T:function(){return i},t:function(){return a}});var n=t(81641);const o=n.J1`
  query GetRun($data: MlflowGetRunInput!) @component(name: "MLflow.ExperimentRunTracking") {
    mlflowGetRun(input: $data) {
      apiError {
        helpUrl
        code
        message
      }
      run {
        info {
          runName
          status
          runUuid
          experimentId
          artifactUri
          endTime
          lifecycleStage
          startTime
          userId
        }
        experiment {
          experimentId
          name
          tags {
            key
            value
          }
          artifactLocation
          lifecycleStage
          lastUpdateTime
        }
        modelVersions {
          status
          version
          name
          source
        }
        data {
          metrics {
            key
            value
            step
            timestamp
          }
          params {
            key
            value
          }
          tags {
            key
            value
          }
        }
        inputs {
          datasetInputs {
            dataset {
              digest
              name
              profile
              schema
              source
              sourceType
            }
            tags {
              key
              value
            }
          }
          modelInputs {
            modelId
          }
        }
        outputs {
          modelOutputs {
            modelId
            step
          }
        }
      }
    }
  }
`,a=({runUuid:e,disabled:r=!1})=>{var t,a;const{data:i,loading:l,error:s,refetch:d}=(0,n.IT)(o,{variables:{data:{runId:e}},skip:r});return{loading:l,data:null===i||void 0===i||null===(t=i.mlflowGetRun)||void 0===t?void 0:t.run,refetchRun:d,apolloError:s,apiError:null===i||void 0===i||null===(a=i.mlflowGetRun)||void 0===a?void 0:a.apiError}},i=()=>(0,n._l)(o)}}]);