import Box from '@mui/material/Box'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import { useState } from 'react'

import { SummaryResponseBody } from "./types"
import { VideoInfo } from './VideoInfo'
import { DetailSummary } from './DetailSummary'
import { Topic } from './Topic'
import { QA } from './QA'


interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

interface ResultProps {
    summary: SummaryResponseBody
}

function TabPanel (props: TabPanelProps) {
    const { children, value, index, ...other } = props;
    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            {...other}
        >
            {value === index && (
                <Box sx={{ p: 3 }}>
                    {children}
                </Box>
            )}
        </div>
    );
}


export function Result (props: ResultProps) {
    const { summary } = props;
    const [ value, setValue ] = useState<number>(0)

    const tabItemList: string[] = ['概要', 'トピック', '詳細', 'QA']

    const onTabChangeHandler = (_: React.SyntheticEvent, value: number) => {
        setValue(value);
    }

    return (
        <>
            <Box sx={{ width: '100%', bgcolor: 'background.paper', marginTop: 3 }}>
                <Tabs
                    value={value}
                    onChange={onTabChangeHandler}
                    centered
                >
                    {tabItemList.map((item, idx) =>
                        <Tab key={idx} label={item} />
                    )}
                </Tabs>
            </Box>
            <TabPanel value={value} index={0}>
                <VideoInfo summary={summary.summary} />
            </TabPanel>
            <TabPanel value={value} index={1}>
                <Topic summary={summary.summary} />
            </TabPanel>
            <TabPanel value={value} index={2}>
                <DetailSummary summary={summary.summary} />
            </TabPanel>
            <TabPanel value={value} index={3}>
                <QA />
            </TabPanel>
        </>
    ) 
}