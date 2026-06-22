import { defineStore } from "pinia";
import { ref } from "vue";
import { dataProvider } from "@/data";
import type { GraphQuery, GraphSubgraph } from "@/domain/types";

export const useGraphStore=defineStore("graph",()=>{
  const data=ref<GraphSubgraph>({nodes:[],edges:[]}),loading=ref(false),loaded=ref(false),error=ref("");
  const lastQuery=ref<GraphQuery>({});
  async function load(force=false,query:GraphQuery=lastQuery.value){if(loaded.value&&!force&&JSON.stringify(query)===JSON.stringify(lastQuery.value))return;loading.value=true;error.value="";lastQuery.value=query;try{data.value=await dataProvider.graph.getPanorama(query);loaded.value=true;}catch(e){error.value=e instanceof Error?e.message:"加载失败";}finally{loading.value=false;}}
  async function getNode(nodeId:string){return dataProvider.graph.getNode(nodeId);}
  async function expand(nodeId:string,depth=2){data.value=await dataProvider.graph.expand(nodeId,depth);return data.value;}
  async function search(query:string,type?:string){data.value=await dataProvider.graph.search(query,type);return data.value;}
  async function findPath(fromId:string,toId:string){data.value=await dataProvider.graph.path(fromId,toId);return data.value;}
  return {data,loading,loaded,error,lastQuery,load,refresh:()=>load(true,lastQuery.value),getNode,expand,search,findPath};
});
