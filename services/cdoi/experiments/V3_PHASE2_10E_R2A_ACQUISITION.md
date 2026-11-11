# V3 Phase 2.10E-R2A Acquisition

```json
{
  "cases": [
    {
      "acquisition_status": "CACHED",
      "case_id": "re2ob_checkoutservice_cpu_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "CPU",
      "last_failure_reason": null,
      "last_r2_acquisition_status": "CACHED",
      "preserved_r2_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 158037,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/metrics.parquet",
          "sha256": "761de264537cd3134834cca7cf90d230683a60d58ca0a0a35e538096e701383e",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:14:35.557465Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 347965,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/logs.parquet",
          "sha256": "af5f8e086ac423727abbe07a45dfc3647cb8614e87cec2647f7f1b28b4262da4",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:14:35.559460Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 10277460,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/traces.parquet",
          "sha256": "05b3971a30ddd08f70fc08f39380a551ec2d03672c9df9657ca728d3f9e745aa",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:14:35.582399Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_mem_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_checkoutservice_mem_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "MEM",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED",
      "preserved_r2a_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 174494,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/metrics.parquet",
          "sha256": "51fafedd0f3f0d8a0075adf3c23f9414708f4f1d2da85cf384b8165b31b26f09",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:14:35.584394Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 335235,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/logs.parquet",
          "sha256": "62dc94f259a7c644a35f2accff1f30bf070532cdd286a2e2b11429f99a6a046c",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:14:35.586388Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 10179545,
          "method": "full_download",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/traces.parquet",
          "remote_etag": "\"ddb012f4339e662ce3a82ebe71c506e69f2333a1e6647c4f1a9ce0f0913071db\"",
          "sha256": "ca7f15c502c6e7453169cfa3d76f0476083148f905ddf2712da802b086b8e30c",
          "status": "DOWNLOADED",
          "timestamp": "2026-09-22T07:14:38.166100Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_checkoutservice_socket_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_checkoutservice_socket_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "SOCKET",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED"
    },
    {
      "acquisition_status": "CACHED",
      "case_id": "re2ob_currencyservice_disk_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "DISK",
      "last_failure_reason": null,
      "last_r2_acquisition_status": "CACHED",
      "preserved_r2_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 162150,
          "method": "full_download",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/metrics.parquet",
          "remote_etag": "\"d801471723c2133f4176176df4327c34c16ee1ec0627867759bf8bb80e388d05\"",
          "sha256": "a31419d13452d1c969f8dd22ab82089fe77c8fa3ae2ca4aadeb17180849f17fc",
          "status": "DOWNLOADED",
          "timestamp": "2026-09-22T07:15:12.452132Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 223888,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/logs.parquet",
          "sha256": "aaa390fe2f92a3ae646fb59a6c2069e4a3f9fd789aa3d86f939656d2e55bc366",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:12.453129Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 7734168,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/traces.parquet",
          "sha256": "ebba409588650edab31d79d02819af64edbf3e17e5359f320893fc30f9b8fea7",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:12.472079Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_currencyservice_loss_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_currencyservice_loss_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "LOSS",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED"
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 156391,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/metrics.parquet",
          "sha256": "52752452d9f2fdb69cec2b7575b617f84419131338fcb1c2e1829ef5c242e586",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.563016Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 337106,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/logs.parquet",
          "sha256": "5b0eff42c36df03f4b618f79fea5e0e6f95d54e9afe0e857c86b68696bf72f05",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.565011Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 10155267,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/traces.parquet",
          "sha256": "c98764ff45836b7514480c515a4e0bfe685fb0ce15de8484eae012451b5aea6e",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.588946Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_cpu_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_emailservice_cpu_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "CPU",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED",
      "preserved_r2a_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 153820,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/metrics.parquet",
          "sha256": "888dae20bf94fe78534fe3e2bb821b898ab66f53e2c87101d21466c0fb88aea1",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.590941Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 336154,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/logs.parquet",
          "sha256": "9f742c0c42f0739222db8c92d5d716e1a94a1774d66cb82de3e5bbd64744f9aa",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.593935Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 10184723,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/traces.parquet",
          "sha256": "569e86b874736c9815ea4be07726a4abe4a76990c93c1b992e356b686fed1a9d",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.616872Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_emailservice_delay_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_emailservice_delay_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "DELAY",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED",
      "preserved_r2a_result": true
    },
    {
      "acquisition_status": "CACHED",
      "case_id": "re2ob_emailservice_socket_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "SOCKET",
      "last_failure_reason": null,
      "last_r2_acquisition_status": "CACHED",
      "preserved_r2_result": true
    },
    {
      "acquisition_status": "CACHED",
      "case_id": "re2ob_productcatalogservice_loss_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "LOSS",
      "last_failure_reason": null,
      "last_r2_acquisition_status": "CACHED",
      "preserved_r2_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 162407,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/metrics.parquet",
          "sha256": "ac6b3d751f45963eca95d66f771123cd10b862eabd4783d4138e467c72c1f267",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.618866Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 258741,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/logs.parquet",
          "sha256": "406d5a3988dcfb66b2848e7d6b4d34959fffae04beda74c70c6dc86876010544",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.619864Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 8512907,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/traces.parquet",
          "sha256": "0295a4c78cdb39db6559530d5660cb4ebe1cba340bc03be004b25ffe7be436c5",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.639810Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_productcatalogservice_mem_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_productcatalogservice_mem_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "MEM",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED",
      "preserved_r2a_result": true
    },
    {
      "acquisition_status": "CACHED",
      "case_id": "re2ob_recommendationservice_delay_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "DELAY",
      "last_failure_reason": null,
      "last_r2_acquisition_status": "CACHED",
      "preserved_r2_result": true
    },
    {
      "acquisition_status": "CACHED",
      "artifacts": [
        {
          "artifact": "metrics.parquet",
          "bytes": 155684,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/metrics.parquet",
          "sha256": "667c022923e804d160d01e04b70c18ae78f11ffd36f6b2b7886da80231784d79",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.642775Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/metrics.parquet?download=true"
        },
        {
          "artifact": "logs.parquet",
          "bytes": 333193,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/logs.parquet",
          "sha256": "76b12645aadb2e005cc73f82258a0943298380fa61ce4e3c72c60d50fd53868b",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.644801Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/logs.parquet?download=true"
        },
        {
          "artifact": "traces.parquet",
          "bytes": 10128918,
          "method": "validated_local_cache",
          "path": "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/traces.parquet",
          "sha256": "67772f4dab6993826d873c5b2cab5201c3653f9da23e8c02ab98f8dd17d57ff5",
          "status": "CACHED",
          "timestamp": "2026-09-22T07:15:33.668185Z",
          "url": "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e/re2ob_recommendationservice_disk_1/traces.parquet?download=true"
        }
      ],
      "case_id": "re2ob_recommendationservice_disk_1",
      "evaluation_status": "EVALUATED_GT_MISSED",
      "fault_type": "DISK",
      "last_failure_reason": "URLError: <urlopen error [WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>",
      "last_r2_acquisition_status": "DOWNLOAD_FAILED",
      "preserved_r2a_result": true
    }
  ],
  "dataset_revision": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e",
  "schema_version": "v3_phase2_10e_r2a_acquisition_manifest_v1"
}
```
