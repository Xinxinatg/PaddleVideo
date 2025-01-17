# END=1500
# for ((i=1;i<=END;i++)); do
#     python prepare_dataset.py
# done
import os
import json
import numpy as np
import pickle
import sys
"""
 This python script is used to convert keypoint results of UR FALL dataset
   for training by PaddleVideo
"""


def self_norm(kpt, bbox):
    # kpt: (2, T, 17, 1),  bbox: (T, 4)
    tl = bbox[:, 0:2]
    wh = bbox[:, 2:]
    tl = np.expand_dims(np.transpose(tl, (1, 0)), (2, 3))
    wh = np.expand_dims(np.transpose(wh, (1, 0)), (2, 3))

    res = (kpt - tl) / wh
    res *= np.expand_dims(np.array([[384.], [512.]]), (2, 3))
    return res


def convert_to_ppvideo(all_kpts, all_scores, all_bbox,json_path):
    # shape of all_kpts is (T, 17, 2)
    # print('keypoint.shape',all_kpts.shape)
    if all_kpts.shape[0]==0:
           os.remove(json_path)
           sys.exit("Error message")
    keypoint = np.expand_dims(np.transpose(all_kpts, [2, 0, 1]),
                              -1)  #(2, T, 17, 1)
    keypoint = self_norm(keypoint, all_bbox)

    scores = all_scores
    if keypoint.shape[1] >50:
#         frame_start = (keypoint.shape[1] - 100) // 2
        keypoint = keypoint[:, -50:, :, :]
        scores = all_scores[-50:, :, :]
    elif keypoint.shape[1] < 50:
        keypoint = np.concatenate([
            keypoint,
            np.zeros((2, 50 - keypoint.shape[1], 17, 1), dtype=keypoint.dtype)
        ], 1)
        scores = np.concatenate([
            all_scores,
            np.zeros((50- all_scores.shape[0], 17, 1), dtype=keypoint.dtype)
        ], 0)
    else:
        keypoint = keypoint
        scores = scores
    assert keypoint.shape==(2,50,17,1)

    return keypoint, scores


def decode_json_path(json_path):
    content = json.load(open(json_path))
    content = sorted(content, key=lambda x: x[0])
    all_kpts = []
    all_score = []
    all_bbox = []
    for annos in content:
        bboxes = annos[1]
        kpts = annos[2][0]
        frame_id = annos[0]

        if len(bboxes) != 1:
            continue
        kpt_res = []
        kpt_score = []
        for kpt in kpts[0]:
            x, y, score = kpt
            kpt_res.append([x, y])
            kpt_score.append([score])
        all_kpts.append(np.array(kpt_res))
        all_score.append(np.array(kpt_score))
        all_bbox.append([
            bboxes[0][0], bboxes[0][1], bboxes[0][2] - bboxes[0][0],
            bboxes[0][3] - bboxes[0][1]
        ])
    all_kpts_np = np.array(all_kpts)
    all_score_np = np.array(all_score)
    all_bbox_np = np.array(all_bbox)
    # print('json_path',json_path)
    video_anno, scores = convert_to_ppvideo(all_kpts_np, all_score_np,
                                            all_bbox_np,json_path)

    return video_anno, scores


if __name__ == '__main__':
    all_keypoints = []
    all_labels = [[], []]
    all_scores = []
    for i, path in enumerate(os.listdir("nega_jsons2")):
        video_anno, score = decode_json_path(os.path.join("nega_jsons2", path))

        all_keypoints.append(video_anno)
        all_labels[0].append(str(i))
        all_labels[1].append(0)  #label 0 means falling
        all_scores.append(score)
    all_data = np.stack(all_keypoints, 0)
    all_score_data = np.stack(all_scores, 0)
    np.save(f"train_data.npy", all_data)
    pickle.dump(all_labels, open(f"train_label.pkl", "wb"))
    np.save("kptscore_data.npy", all_score_data)
